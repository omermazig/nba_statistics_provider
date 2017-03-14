"""
All sort of util functions to help other classes with calculations
"""
from __future__ import division
import functools
import os
import csv
import collections

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


def get_per_game_from_total_stats(stat_dict):
    """

    :param stat_dict:
    :type stat_dict: dict
    """
    per_game_stat_dict = {}
    if 'GP' in stat_dict:
        games_denominator = stat_dict['GP']
    elif 'G' in stat_dict:
        games_denominator = stat_dict['G']
    else:
        raise Exception('No "games" value in dict')

    for k, v in stat_dict.items():
        if k in values_to_adjust_to_per_game_mode:
            per_game_stat_dict[k] = PrettyFloat(v / games_denominator)
        else:
            per_game_stat_dict[k] = v

    return per_game_stat_dict


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

    combined_game_stats = join_stat_dicts(game_logs_list, keys_to_discard, keys_to_sum, keys_to_take_first,
                                          percentage_keys_to_create_back)
    return combined_game_stats


def join_stat_dicts(dicts_list, keys_to_discard=None, keys_to_sum=None, keys_to_take_first=None,
                    percentage_keys_to_create_back=None, wage_key=None):
    """

    :param dicts_list:
    :type dicts_list: list[dict]
    :param keys_to_discard:
    :type keys_to_discard: list[str]
    :param keys_to_sum:
    :type keys_to_sum: list[str]
    :param keys_to_take_first:
    :type keys_to_take_first: list[str]
    :param percentage_keys_to_create_back:
    :type percentage_keys_to_create_back: list[str]
    :param wage_key:
    :type wage_key: str
    :return: A dict with the calculated stats for all the dicts
    :rtype: dict
    """
    keys_to_discard = [] if keys_to_discard is None else keys_to_discard
    keys_to_sum = [] if keys_to_sum is None else keys_to_sum
    keys_to_take_first = [] if keys_to_take_first is None else keys_to_take_first
    percentage_keys_to_create_back = [] if percentage_keys_to_create_back is None else percentage_keys_to_create_back

    number_of_dicts = len(dicts_list)

    if not dicts_list:
        return dicts_list

    dict1 = {}
    for key in dicts_list[0].keys():
        dict1[key] = []

    for game_log in dicts_list:
        for key, value in game_log.items():
            dict1[key].append(value)

    dict2 = {}
    for key, value in dict1.items():
        value = [i for i in value if i is not None]
        if not value:
            dict2[key] = None
        if key in keys_to_discard:
            # dict1.pop(key)
            pass
        elif key in keys_to_take_first:
            dict2[key] = value[0]
        elif key in keys_to_sum:
            dict2['TOTAL_' + key] = functools.reduce(lambda x, y: x + y, value)
        # Can't use "sum" cause WL are strings
        elif key not in percentage_keys_to_create_back and key is not wage_key:
            if wage_key is None:
                dict2[key] = functools.reduce(lambda x, y: x + y, value) / float(len(value))
            else:
                numerator = 0
                divisor = 0
                for index in range(number_of_dicts):
                    numerator += value[index] * dict1[wage_key][index]
                    divisor += dict1[wage_key][index]
                dict2[key] = numerator / divisor if divisor != 0 else 0

    if wage_key:
        dict2['TOTAL_' + wage_key] = sum(dict1[wage_key])

    for key in percentage_keys_to_create_back:
        dict2[key] = dict2[key.replace('_PCT', 'M')] / float(dict2[key.replace('_PCT', 'A')])

    if 'TOTAL_WL' in dict2.keys():
        wins_and_losses = dict2.pop('TOTAL_WL')
        dict2['TOTAL_W'] = wins_and_losses.count('W')
        dict2['TOTAL_L'] = wins_and_losses.count('L')

    dict2['NUM_OF_ITEMS'] = number_of_dicts

    return dict2


def join_advanced_lineup_dicts(lineup_dicts):
    """

    :param lineup_dicts:
    :type lineup_dicts:list[dict]
    :return:
    :rtype: dict
    """
    keys_to_discard = ['W',
                       'W_PCT',
                       'L',
                       'GROUP_SET',
                       'GROUP_NAME',
                       'GROUP_ID',
                       'GP',
                       ]
    keys_to_sum = ['MIN']

    for lineup_dict in lineup_dicts:
        number_of_possessions = (lineup_dict['MIN'] / 48) * lineup_dict['PACE']
        lineup_dict['POS'] = number_of_possessions

    if not lineup_dicts:
        return dict()
    else:
        return join_stat_dicts(lineup_dicts, keys_to_discard=keys_to_discard, keys_to_sum=keys_to_sum, wage_key='POS')


def convert_dicts_into_csv(dicts_to_convert, primary_key, csv_path):
    """
    :param dicts_to_convert: A list of the dicts that will be converted into a single table. The keys most be identical.
    :type dicts_to_convert: list[dict]
    :param primary_key:
    :type primary_key: str
    :param csv_path: Path to the output csv file
    :type csv_path: str
    """
    if not type(dicts_to_convert) == list:
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


def calculate_effective_field_goal_percent(field_goal_makes, three_pointer_makes, field_goal_attempts):
    """
    :param field_goal_makes: field_goal_makes
    :type field_goal_makes: field_goal_makes
    :param three_pointer_makes: three_pointer_makes
    :type three_pointer_makes: three_pointer_makes
    :param field_goal_attempts: field_goal_attempts
    :type field_goal_attempts: field_goal_attempts
    :return:The EFG%
    :rtype:float
    """
    if field_goal_attempts == 0:
        effective_field_goal_percentage = 0
    else:
        effective_field_goal_percentage = (field_goal_makes + (0.5 * three_pointer_makes)) / field_goal_attempts
    return effective_field_goal_percentage


def calculate_ppp_from_effective_field_goal_percent(effective_field_goal_percent):
    """

    :param effective_field_goal_percent:
    :type effective_field_goal_percent:
    :return:
    :rtype:
    """
    return PrettyFloat(effective_field_goal_percent * 2)


def get_effective_field_goal_relevant_data_from_multiple_shot_charts(shot_charts):
    """
    Receives a list of shot charts, and returns a tuple with the relevant data to calculate effective field goal
    percentage
    :param shot_charts: Any object describing made and missed shots with 2 and 3 point divide
    :type shot_charts: list[dict]
    :return: tuple of:
    The number of field goals made,
    The number of 3 point field goals made,
    The number of field goals attempted
    :rtype: tuple(int, int, int)
    """
    field_goal_makes = 0
    three_pointer_makes = 0
    field_goal_attempts = 0
    for shot_chart in shot_charts:
        field_goal_makes += shot_chart["FGM"]
        three_pointer_makes += shot_chart["FG3M"]
        field_goal_attempts += shot_chart["FGA"]

    if field_goal_attempts == 0:
        return 0, 0, 0
    else:
        return field_goal_makes, three_pointer_makes, field_goal_attempts


def get_effective_field_goal_percentage_from_multiple_shot_charts(shot_charts):
    """
    Receives a list of shot charts, and returns the effective field goal percentage, alongside with the number of shots
    EFG% = FGM + (0.5 * FG3M) / FGA
    :param shot_charts: Any object describing made and missed shots with 2 and 3 point divide
    :type shot_charts: list[dict]
    :return: tuple of the EFG% on uncontested shots, and the amount of those shots.
    :rtype: tuple(float)
    """
    field_goal_makes, three_pointer_makes, field_goal_attempts = \
        get_effective_field_goal_relevant_data_from_multiple_shot_charts(shot_charts)
    if field_goal_attempts == 0:
        return 0, 0
    else:
        return calculate_effective_field_goal_percent(field_goal_makes, three_pointer_makes,
                                                      field_goal_attempts), field_goal_attempts


def _get_list_of_players_ids_from_lineup_dict(lineup_dict_to_convert):
    """
    Name
    :param lineup_dict_to_convert: Lineup dict from goldsberry
    :type lineup_dict_to_convert: dict
    :return: All 5 player ids of players in the lineup
    :rtype: list[int]
    """
    return map(int, lineup_dict_to_convert['GROUP_ID'].split(' - '))


def _get_list_of_players_ids_from_players_object_list(players_object_list):
    """
    Name
    :param players_object_list: List of players object list
    :type players_object_list: list[playerScripts.NBAPlayer]
    :return: All 5 player ids of players in the lineup
    :rtype: list[int]
    """
    return map(lambda player_object: player_object.id, players_object_list)


def _does_lineup_contains_players_from_list(lineup_dict, players_object_list, check_all_players):
    """
    Return whether or not there's a player from a list in a lineup
    :param lineup_dict:
    :type lineup_dict: dict
    :param players_object_list:
    :type players_object_list: list[playerScripts.NBAPlayer]
    :param check_all_players: Is single player's appearance in the lineup enough to return to determine result
    :type check_all_players: bool
    :return:
    :rtype: bool
    """

    lineup_players_ids_list = _get_list_of_players_ids_from_lineup_dict(lineup_dict)
    listed_players_ids_list = _get_list_of_players_ids_from_players_object_list(players_object_list)
    if check_all_players:
        return set(lineup_players_ids_list).issuperset(listed_players_ids_list)
    else:
        return bool(set(lineup_players_ids_list).intersection(listed_players_ids_list))


def is_lineup_valid(lineup_dict, white_list, black_list):
    """
    Both lists empty - Every lineup is good
    Only white list full - If all players from white list in lineup
    Only black list full - If all players in black list not in lineup
    Both lists full - If all players from white list in lineup, and all players in black list not in lineup
    :param lineup_dict:
    :type lineup_dict: dict
    :param white_list:
    :type white_list: list[playerScripts.NBAPlayer]
    :param black_list:
    :type black_list: list[playerScripts.NBAPlayer]
    :return:
    :rtype: bool
    """
    if _does_lineup_contains_players_from_list(lineup_dict, black_list, check_all_players=False):
        return False
    elif white_list is [] or _does_lineup_contains_players_from_list(lineup_dict, white_list, check_all_players=True):
        return True
    else:
        return False


def get_most_recent_stat_dict(stat_dict_list):
    """
    Returns the TOTAL stat dict if the player played for only one team, and THE STAT DICT FOR THE LATEST TEAM if the
    player played for more then one team.

    :param stat_dict_list: List of all the stat dicts. Length could be 1 (one team) or 3+ (2+ team and TOTAL)
    :type stat_dict_list: list[dict]
    :return: The desired stat dict
    :rtype: dict
    """
    if len(stat_dict_list) == 0:
        return None
    elif len(stat_dict_list) == 1:
        return  stat_dict_list[0]
    else:
        return stat_dict_list[-2]
