from __future__ import division
import functools
import os
import pickle

from leagueScripts import league_object_pickle_path_regex


pickles_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pythonPickles')
csvs_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'csvs')


def join_player_single_game_stats(game_logs_list):
    keys_to_discard = ['GAME_DATE',
                       'Game_ID',
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

    combined_game_stats = join_stat_dicts(game_logs_list, keys_to_discard, keys_to_sum, keys_to_take_first,
                                          percentage_keys_to_create_back)
    combined_game_stats.update({'G': len(game_logs_list)})
    return combined_game_stats


def join_stat_dicts(dicts_list, keys_to_discard=None, keys_to_sum=None, keys_to_take_first=None,
                    percentage_keys_to_create_back=None, wage_key=None):
    keys_to_discard = [] if keys_to_discard is None else keys_to_discard
    keys_to_sum = [] if keys_to_sum is None else keys_to_sum
    keys_to_take_first = [] if keys_to_take_first is None else keys_to_take_first
    percentage_keys_to_create_back = [] if percentage_keys_to_create_back is None else percentage_keys_to_create_back

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
        if key in keys_to_discard:
            # dict1.pop(key)
            pass
        elif key in keys_to_take_first:
            dict2[key] = dict1[key][0]
        elif key in keys_to_sum:
            dict2['TOTAL_' + key] = functools.reduce(lambda x, y: x + y, dict1[key])
        # Can't use "sum" cause WL are strings
        elif key not in percentage_keys_to_create_back and key is not wage_key:
            if wage_key is None:
                dict2[key] = functools.reduce(lambda x, y: x + y, dict1[key]) / float(len(dict1[key]))
            else:
                numerator = 0
                divisor = 0
                for index in range(len(dicts_list)):
                    numerator += dict1[key][index] * dict1[wage_key][index]
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

    return dict2


def join_advanced_lineup_dicts(lineup_dicts):
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
        return lineup_dicts
    else:
        return join_stat_dicts(lineup_dicts, keys_to_discard=keys_to_discard, keys_to_sum=keys_to_sum, wage_key='POS')


def convert_dicts_into_csv(dicts_to_convert, csv_path):
    """
    :param dicts_to_convert: A list of the dicts that will be converted into a single table. The keys most be identical.
    :type dicts_to_convert: list
    :param csv_path: Path to the output csv file
    :type csv_path: str
    """
    import csv

    if not type(dicts_to_convert) == list:
        dicts_to_convert = [dicts_to_convert]
    with open(csv_path, 'w') as csvfile:
        fieldnames = ['category'] + dicts_to_convert[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for dict_to_enter in dicts_to_convert:
            writer.writerow(dict_to_enter)


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
    :type players_object_list: list[NBAPlayer]
    :return: All 5 player ids of players in the lineup
    :rtype: list[int]
    """
    return map(lambda player_object: player_object.player_id, players_object_list)


def _does_lineup_contains_players_from_list(lineup_dict, players_object_list, check_all_players):
    """
    Return whether or not there's a player from a list in a lineup
    :param lineup_dict:
    :type lineup_dict:
    :param players_object_list:
    :type players_object_list:
    :return:
    :rtype:
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
    Only white list full - Only players in white list
    Only black list full - Only players not in white list
    Both lists full - Only players in white list, Only players not in white list
    :param lineup_dict:
    :type lineup_dict:
    :param white_list:
    :type white_list:
    :param black_list:
    :type black_list:
    :return:
    :rtype:
    """
    if _does_lineup_contains_players_from_list(lineup_dict, black_list, check_all_players=False):
        return False
    elif white_list is [] or _does_lineup_contains_players_from_list(lineup_dict, white_list, check_all_players=True):
        return True
    else:
        return False


def is_lineup_all_shooters(lineup_dict, attempts_limit=20):
    """
    :param lineup_dict: Lineup to check
    :type lineup_dict: dict
    :param attempts_limit: attempts_limit
    :type attempts_limit: int
    :return: Whether or not every player in the lineup has shot more threes than the attempts limit
    :rtype: bool
    """
    for player_id in _get_list_of_players_ids_from_lineup_dict(lineup_dict):
        from playerScripts import NBAPlayer
        player_object = NBAPlayer(player_name_or_id=player_id)
        if not player_object.is_three_point_shooter(attempts_limit=attempts_limit):
            return False
    else:
        return True


def get_cached_league_object(season='2015'):
    with open(league_object_pickle_path_regex.format(season=season),
              "rb") as file1:
        player_objects_2015 = pickle.load(file1)
    return player_objects_2015
