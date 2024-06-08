"""
All sort of util functions to help other classes with calculations
"""
import collections
import csv
import functools
import logging
import os
import re
import sys
import time
from contextlib import contextmanager
# This import is only for type hinting, so I don't care it's private
# noinspection PyProtectedMember
from nba_api.stats.endpoints._base import Endpoint
from pandas import DataFrame
from typing import TypeVar, Optional

pickles_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pythonPickles')
csvs_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'csvs')

values_to_adjust_to_per_game_mode = ['AST',
                                     'BLK',
                                     'DREB',
                                     'FG2A',
                                     'FG2M',
                                     'FG3A',
                                     'FG3M',
                                     'FGA',
                                     'FGM',
                                     'FTA',
                                     'FTM',
                                     'MIN',
                                     'OREB',
                                     'PF',
                                     'PTS',
                                     'REB',
                                     'STL',
                                     'TOV',
                                     'D_FGA',
                                     'D_FGM',
                                     'PASS',
                                     'C_DREB',
                                     'C_OREB',
                                     'C_REB',
                                     'UC_DREB',
                                     'UC_OREB',
                                     'UC_REB',
                                     ]


class PrettyFloat(float):
    """
    A float that has a better print
    """

    def __repr__(self):
        return "%0.2f" % self


class Loggable:
    """
    Class that can log
    """
    logger: logging.Logger = None

    class __CustomFormatter(logging.Formatter):
        grey = "\x1b[38;21m"
        yellow = "\x1b[33;21m"
        red = "\x1b[31;21m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"
        format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

        FORMATS = {
            logging.DEBUG: grey + format + reset,
            logging.INFO: grey + format + reset,
            logging.WARNING: yellow + format + reset,
            logging.ERROR: red + format + reset,
            logging.CRITICAL: bold_red + format + reset
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt)
            return formatter.format(record)

    def __init__(self):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.__CustomFormatter())
        logging.basicConfig(level=logging.INFO,
                            datefmt='%Y-%m-%d %H:%M:%S',
                            handlers=[handler])
        self.logger = logging.getLogger(__name__)


def get_per_game_from_total_stats(stats_df: DataFrame):
    if 'GP' in stats_df:
        games_denominator = stats_df['GP']
    elif 'G' in stats_df:
        games_denominator = stats_df['G']
    else:
        raise Exception('No "games" value in dict')

    per_game_stat_df = stats_df.copy()
    for k, v in per_game_stat_df.items():
        if k in values_to_adjust_to_per_game_mode:
            per_game_stat_df[k] = v / games_denominator
        else:
            per_game_stat_df[k] = v

    return per_game_stat_df


def join_single_game_stats(game_logs_list, per_36=False):
    """

    :param game_logs_list:
    :type game_logs_list:list[dict]
    :param per_36: Whether to measure all the relevant stats categories so they will be per 36 minutes
    :type per_36: bool
    :return:
    :rtype: dict
    """
    keys_to_discard = ['GAME_DATE',
                       'Game_ID',
                       'GAME_ID',
                       'MATCHUP',
                       'VIDEO_AVAILABLE',
                       'SEASON_ID'
                       ]
    keys_to_sum = ['PLUS_MINUS',
                   'WL']
    keys_to_take_first = ['Player_ID',
                          'SEASON_ID']

    percentage_keys_to_create_back = ['FG3_PCT',
                                      'FG_PCT',
                                      'FT_PCT']
    if per_36:
        game_logs_to_remove = []
        keys_to_not_divide = keys_to_discard + keys_to_sum + keys_to_take_first + percentage_keys_to_create_back + [
            'MIN']
        for game_log in game_logs_list:
            if not game_log['MIN']:
                game_logs_to_remove.append(game_log)
            else:
                for category_name, category_value in game_log.items():
                    if category_name not in keys_to_not_divide:
                        game_log[category_name] = (category_value / game_log['MIN']) * 36
        for game_log in game_logs_to_remove:
            game_logs_list.remove(game_log)

    combined_game_stats = join_stat_df(game_logs_list, keys_to_discard, keys_to_sum, keys_to_take_first,
                                       percentage_keys_to_create_back)
    return combined_game_stats


def join_stat_df(
        df: DataFrame,
        keys_to_discard: Optional[list[str]] = None,
        keys_to_sum: Optional[list[str]] = None,
        keys_to_take_first: Optional[list[str]] = None,
        percentage_keys_to_create_back: Optional[list[str]] = None,
        wage_key: str = None
) -> DataFrame:
    # TODO - Check!
    keys_to_discard = [] if keys_to_discard is None else keys_to_discard
    keys_to_sum = [] if keys_to_sum is None else keys_to_sum
    keys_to_take_first = [] if keys_to_take_first is None else keys_to_take_first
    percentage_keys_to_create_back = [] if percentage_keys_to_create_back is None else percentage_keys_to_create_back

    number_of_entries = len(df)

    if df.empty:
        return df

    dict1 = {}
    for key in df.columns:
        dict1[key] = []

    for _, row in df.iterrows():
        for key, value in row.items():
            dict1[key].append(value)

    dict2 = {}
    for key, value in dict1.items():
        value = [i for i in value if i is not None]
        if not value:
            dict2[key] = None
        if key in keys_to_discard or key.endswith('RANK'):  # Ranks averages are useless, so we discard them.
            # dict1.pop(key)
            continue
        elif key in keys_to_take_first:
            dict2[key] = value[0]
        elif key in keys_to_sum:
            # Can't use "sum" cause WL are strings
            dict2['TOTAL_' + key] = functools.reduce(lambda x, y: x + y, value)
        elif key not in percentage_keys_to_create_back and key is not wage_key:
            if wage_key is None:
                dict2[key] = functools.reduce(lambda x, y: x + y, value) / float(len(value))
            else:
                numerator = 0
                divisor = 0
                for index in range(number_of_entries):
                    numerator += value[index] * dict1[wage_key][index]
                    divisor += dict1[wage_key][index]
                dict2[key] = numerator / divisor if divisor != 0 else 0

    if wage_key:
        dict2['TOTAL_' + wage_key] = sum(dict1[wage_key])

    for key in percentage_keys_to_create_back:
        try:
            dict2[key] = dict2[key.replace('_PCT', 'M')] / float(dict2[key.replace('_PCT', 'A')])
        except ZeroDivisionError:
            dict2[key] = 0

    if 'TOTAL_WL' in dict2.keys():
        wins_and_losses = dict2.pop('TOTAL_WL')
        dict2['TOTAL_W'] = wins_and_losses.count('W')
        dict2['TOTAL_L'] = wins_and_losses.count('L')

    dict2['NUM_OF_ITEMS'] = number_of_entries

    return DataFrame({k: [v] for k, v in dict2.items()})


def join_advanced_lineup_df(lineups_df: DataFrame) -> DataFrame:
    keys_to_discard = ['W',
                       'W_PCT',
                       'L',
                       'GROUP_SET',
                       'GROUP_NAME',
                       'GROUP_ID',
                       'GP',
                       ]
    keys_to_sum = ['MIN']

    if lineups_df.empty:
        return lineups_df
    else:
        return join_stat_df(lineups_df, keys_to_discard=keys_to_discard, keys_to_sum=keys_to_sum, wage_key='POSS')


def convert_dicts_into_csv(dicts_to_convert, primary_key, csv_path):
    """
    :param dicts_to_convert: A list of the dicts that will be converted into a single table. The keys most be identical.
    :type dicts_to_convert: list[dict]
    :param primary_key:
    :type primary_key: str
    :param csv_path: Path to the output csv file
    :type csv_path: str
    """
    if not isinstance(dicts_to_convert, list):
        raise Exception('Has to be a list of dicts')
    with open(csv_path, 'w') as csvfile:
        fieldnames = list(dicts_to_convert[0].keys())
        # Moving the primary key to the top of the fieldnames list
        fieldnames.insert(0, fieldnames.pop(fieldnames.index(primary_key)))
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for dict_to_enter in dicts_to_convert:
            ordered_dict_to_enter = collections.OrderedDict()
            primary_value = dict_to_enter.pop(primary_key)
            ordered_dict_to_enter.update({primary_key: primary_value})
            ordered_dict_to_enter.update(dict_to_enter)
            writer.writerow(ordered_dict_to_enter)


def convert_dict_of_dicts_into_csv(dict_of_dicts_to_convert, csv_path, original_dict_key_description='Category'):
    """

    :param dict_of_dicts_to_convert:
    :type dict_of_dicts_to_convert: dict[dict]
    :param csv_path:
    :type csv_path: str
    :param original_dict_key_description:
    :type original_dict_key_description: str
    :return: nothing
    :rtype: None
    """
    list_of_dicts_to_convert = _convert_dict_of_dicts_into_list_of_dicts(dict_of_dicts_to_convert,
                                                                         original_dict_key_description)
    convert_dicts_into_csv(list_of_dicts_to_convert, original_dict_key_description, csv_path)


def _convert_dict_of_dicts_into_list_of_dicts(dict_of_dicts_to_convert, original_dict_key_description):
    """

    :param dict_of_dicts_to_convert:
    :type dict_of_dicts_to_convert: dict[dict]
    :param original_dict_key_description:
    :type original_dict_key_description: str
    :return:
    :rtype:list[dict]
    """
    list_of_dicts_to_return = []
    for k, v in dict_of_dicts_to_convert.items():
        dict_to_append = v
        dict_to_append[original_dict_key_description] = k
        list_of_dicts_to_return.append(dict_to_append)
    return list_of_dicts_to_return


def calculate_efg_percent(field_goal_makes, three_pointer_makes, field_goal_attempts):
    """
    :param field_goal_makes: field_goal_makes
    :type field_goal_makes: field_goal_makes
    :param three_pointer_makes: three_pointer_makes
    :type three_pointer_makes: three_pointer_makes
    :param field_goal_attempts: field_goal_attempts
    :type field_goal_attempts: field_goal_attempts
    :return: The EFG%
    :rtype: float
    """
    if field_goal_attempts == 0:
        efg_percentage = 0
    else:
        efg_percentage = (field_goal_makes + (0.5 * three_pointer_makes)) / field_goal_attempts
    return efg_percentage


def calculate_ppp_from_efg_percent(efg_percent):
    """

    :param efg_percent:
    :type efg_percent:
    :return:
    :rtype:
    """
    return PrettyFloat(efg_percent * 2)


def get_efg_relevant_data_from_multiple_shot_charts(shot_charts: DataFrame) -> tuple[int, int, int]:
    """
    Receives a list of shot charts, and returns a tuple with the relevant data to calculate effective field goal
    percentage
    :param shot_charts: Any object describing made and missed shots with 2 and 3 point divide
    :return: tuple of:
        The number of field goals made,
        The number of 3 point field goals made,
        The number of field goals attempted
    :rtype: tuple(int, int, int)
    """
    cols = ["FGM", "FG3M", "FGA"]
    field_goal_info = shot_charts[cols].sum(axis=0)
    field_goal_makes = field_goal_info["FGM"]
    three_pointer_makes = field_goal_info["FG3M"]
    field_goal_attempts = field_goal_info["FGA"]

    return field_goal_makes, three_pointer_makes, field_goal_attempts


def get_efg_percentage_from_multiple_shot_charts(shot_charts: DataFrame) -> tuple[float, int]:
    """
    Receives a list of shot charts, and returns the effective field goal percentage, alongside with the number of shots
    EFG% = FGM + (0.5 * FG3M) / FGA
    :param shot_charts: Any object describing made and missed shots with 2 and 3 point divide
    :return: tuple of the EFG% on uncontested shots, and the amount of those shots.
    """
    field_goal_makes, three_pointer_makes, field_goal_attempts = \
        get_efg_relevant_data_from_multiple_shot_charts(shot_charts)
    return calculate_efg_percent(field_goal_makes, three_pointer_makes, field_goal_attempts), field_goal_attempts


def get_stat_summation_from_list(stat_dicts, stat_key):
    """

    :param stat_dicts: A list of all the stat dicts to sum up
    :type stat_dicts: list[dict]
    :param stat_key: The stat to check
    :type stat_key: str
    :return: The sum of all 30 teams value for the given stat key
    :rtype: float
    """
    sum1 = 0
    try:
        for team_stat_object in stat_dicts:
            sum1 += team_stat_object[stat_key]

        return sum1
    except KeyError:
        raise KeyError('Key "%s" does not appear in stat dicts' % stat_key)


def get_stat_average_from_list(stat_dicts, stat_key):
    """

    :param stat_dicts: A list of all the stat dicts to sum up for average
    :type stat_dicts: list[dict]
    :param stat_key: The stat to check
    :type stat_key: str
    :return: The average value of all 30 teams for the given stat key
    :rtype: float
    """
    return get_stat_summation_from_list(stat_dicts, stat_key) / 30.0


def get_num_of_possessions_from_stat_dict(stat_df) -> float:
    """

    :param stat_df: A stat df. Can be for players, teams, leagues or games
    :return: The number of possessions in the events which the df represents
    """
    return (stat_df['FGA'] - stat_df['OREB'] + stat_df['TOV'] + (0.44 * stat_df['FTA'])).sum()


def get_pace_from_stat_dict(stat_dict):
    """

    :param stat_dict: A stat dict. Can be for a player, a team or a game (and etc)
    :type stat_dict: dict
    :return: The number of possessions in the event which the dict represents per 48 minutes
    :rtype: float
    """
    return get_num_of_possessions_from_stat_dict(stat_dict) / stat_dict['MIN']


def _get_list_of_players_ids_from_lineup_df(lineup_dict_to_convert: DataFrame) -> set[int]:
    """
    Name
    :param lineup_dict_to_convert: Lineup dict
    :return: All 5 player ids of players in the lineup
    :rtype: list[int]
    """
    return {int(player_id) for player_id in lineup_dict_to_convert['GROUP_ID'].split('-') if player_id}


def _get_list_of_players_ids_from_players_object_list(players_ids: list[int]):
    """
    Name
    :param players_ids: List of players object list
    :type players_ids: list[playerScripts.NBAPlayer]
    :return: All 5 player ids of players in the lineup
    :rtype: list[int]
    """
    return [player_object.id for player_object in players_ids]


def _does_lineup_contains_players_from_list(
        lineup_df: DataFrame, players_ids: set[int], check_all_players: bool) -> bool:
    """
    Return whether there's a player from a list in a lineup
    :param lineup_df:
    :param players_ids:
    :param check_all_players: Is single player's appearance in the lineup enough to return to determine result
    :return:
    """

    lineup_players_ids_list = _get_list_of_players_ids_from_lineup_df(lineup_df)
    if check_all_players:
        return lineup_players_ids_list.issuperset(players_ids)
    else:
        return bool(lineup_players_ids_list.intersection(players_ids))


def is_lineup_valid(lineup_row: DataFrame, ids_white_list: set[int], ids_black_list: set[int]) -> bool:
    """
    Both lists empty - Every lineup is good
    Only white list full - If all players from white list in lineup
    Only black list full - If all players in black list not in lineup
    Both lists full - If all players from white list in lineup, and all players in black list not in lineup
    :param lineup_row:
    :param ids_white_list:
    :param ids_black_list:
    :return:
    """
    if _does_lineup_contains_players_from_list(lineup_row, ids_black_list, check_all_players=False):
        return False
    elif ids_white_list is [] or _does_lineup_contains_players_from_list(lineup_row, ids_white_list, check_all_players=True):
        return True
    else:
        return False


def get_most_recent_stat_dict(stats_df: DataFrame) -> Optional[DataFrame]:
    """
    Returns the TOTAL stat dict if the player played for only one team, and THE STAT DICT FOR THE LATEST TEAM if the
    player played for more then one team.

    :param stats_df: List of all the stat dicts. Length could be 1 (one team) or 3+ (2+ team and TOTAL)
    :return: The desired stat df
    """
    if len(stats_df) == 0:
        return None
    elif len(stats_df) == 1:
        return stats_df
    else:
        # Last one is TOT, so the one before
        return stats_df[stats_df['TEAM_ABBREVIATION'] == 'TOT']


# noinspection PyPep8Naming
def get_aPER_from_stat_dict(stat_df: DataFrame, team_object) -> float:
    """
    :param stat_df:
    :type stat_df: dict[str, float or str]
    :param team_object:
    :type team_object: teamScripts.NBATeam
    :return: The aPER, which is the PER measurement BEFORE normalization.
    """
    # TODO - Check
    MIN = stat_df['MIN'].item()
    FG3M = stat_df['FG3M'].item()
    AST = stat_df['AST'].item()
    FGM = stat_df['FGM'].item()
    FTM = stat_df['FTM'].item()
    TOV = stat_df['TOV'].item()
    FGA = stat_df['FGA'].item()
    FTA = stat_df['FTA'].item()
    REB = stat_df['REB'].item()
    OREB = stat_df['OREB'].item()
    STL = stat_df['STL'].item()
    BLK = stat_df['BLK'].item()
    PF = stat_df['PF'].item()

    team_ast_percentage = team_object.get_assist_percentage().item()
    pace_adjustment = team_object.get_pace_adjustment().item()

    league_ast_factor = team_object.current_league_object.get_league_assist_factor()
    league_ppp = team_object.current_league_object.get_league_ppp()
    league_dreb_percentage = team_object.current_league_object.get_league_defensive_reb_percentage()
    league_foul_factor = team_object.current_league_object.get_league_foul_factor()

    uPER = (1 / MIN) * (FG3M
                        + (2 / 3) * AST
                        + (2 - league_ast_factor * team_ast_percentage) * FGM
                        + (FTM * 0.5 * (1 + (1 - team_ast_percentage) + (2 / 3) * team_ast_percentage))
                        - league_ppp * TOV
                        - league_ppp * league_dreb_percentage * (FGA - FGM)
                        - league_ppp * 0.44 * (0.44 + (0.56 * league_dreb_percentage)) * (FTA - FTM)
                        + league_ppp * (1 - league_dreb_percentage) * (REB - OREB)
                        + league_ppp * league_dreb_percentage * OREB
                        + league_ppp * STL
                        + league_ppp * league_dreb_percentage * BLK
                        - PF * league_foul_factor)

    return uPER * pace_adjustment


def get_season_from_year(year: int) -> str:
    """
    Get string for the season ('2023-24') from a year (2023)

    :param year: The year
    :return: The season string
    """
    return "{}-{}".format(year, str(year + 1)[2:])


class ActionGapManager:
    """ This is due to the NBA API blocking us if we make requests too frequently. It's a cooldown mechanism"""

    def __init__(self, gap=0.6):
        self.gap = gap
        self.last_action_time = None

    def _wait_for_gap(self):
        if self.last_action_time is not None:
            elapsed_time = time.time() - self.last_action_time
            if elapsed_time < self.gap:
                time.sleep(self.gap - elapsed_time)

    def _update_last_action_time(self):
        self.last_action_time = time.time()

    @contextmanager
    def action_gap(self):
        try:
            self._wait_for_gap()
            yield
        finally:
            self._update_last_action_time()


# This is for not overloading the NBA API and getting blocked
nba_api_cooldown = 0.6
gap_manager = ActionGapManager(gap=nba_api_cooldown)

T = TypeVar("T", bound=Endpoint)


def get_stat_class(stat_class_class_object: type[T], custom_filters: list[tuple[str, str, str]] = None, **kwargs) -> T:
    with gap_manager.action_gap():
        stat_class = stat_class_class_object(get_request=False, **kwargs)
        if custom_filters:
            raise Exception(
                "Custom Filters dont work. Don't know why. Check https://github.com/swar/nba_api/issues/445 for more"
            )
            # noinspection PyUnreachableCode
            stat_class.parameters["CF"] = ":".join("*".join(custom_filter) for custom_filter in custom_filters)
        stat_class.get_request()
    return stat_class


def get_all_seasons_of_pickle_files() -> list[str]:
    pickle_files = os.listdir(pickles_folder_path)
    pattern = r"league_object_(\d{4}-\d{2}).pickle"
    years = [re.match(pattern, file_name).group(1) for file_name in pickle_files if re.match(pattern, file_name)]
    return years
