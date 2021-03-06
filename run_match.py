from team import Team
from colortext import *
import argparse
import os
import random
import shutil
import ansiwrap
from time import sleep
from match_events import *
from utils import *
from visualization import *
from PyQt5 import QtCore, QtGui, QtWidgets
import constants
#import pyautogui

def calc_score(towers, stacks):
    score = 0
    for i in range(3):
        score += stacks[i] * (towers[i] + 1)
    return score

def get_valid_match(towers, red_stacks, blue_stacks): #Checks if match score is valid
    if red_stacks[0] == -1 or blue_stacks[0] == -1: #Score generation failed
        return False
    for i in range(3):
        if towers[i] + red_stacks[i] + blue_stacks[i] > 22:
            return False
    return True

def gen_towers(focus1, focus2):
    towers = [random.randint(0, 1), random.randint(0, 1), random.randint(0, 1)]

    if focus1 == focus2:
        towers[focus1] = random.randint(2, 4)
    else:
        towers[focus1] = random.randint(1, 3)
        towers[focus2] = random.randint(1, 3)
    
    if sum(towers) > 7:
        return gen_towers(focus1, focus2)
    else:
        return towers

def gen_stacks(towers, focus_cube, score):
    stacks = [0, 0, 0]
    max_of_focus = int(score / (towers[focus_cube] + 1))
    #print("Max of focus: " + str(max_of_focus))
    stacks[focus_cube] = random.randint(int(max_of_focus / 2), int(max_of_focus * 3 / 4))
    not_focus = [i for i in range(3) if i != focus_cube]
    attempts = 0
    while calc_score(towers, stacks) != score:
        index = random.randint(0,1)
        add_cube = not_focus[index]
        stacks[add_cube] += 1
        if calc_score(towers, stacks) > score:
            stacks[add_cube] -= 1
            if index == 0:
                stacks[1] += 1
            else:
                stacks[0] += 1
            if calc_score(towers, stacks) > score:
                attempts += 1
                for i in not_focus:
                    stacks[i] == 0
                stacks[focus_cube] = random.randint(int(max_of_focus / 2), max_of_focus)
        if attempts > 10:
            stacks[0] = -1 #Stack generation failed
            return stacks
    return stacks

def update_cubes(curr, delta):
    for i in range(3):
        for j in range(3):
            curr[i][j] += delta[i][j]

def pick_acting_team(strengths):
    random_result = random.uniform(0, sum(strengths))
    if random_result <= strengths[0]:
        strengths[0] /= 2
        return 0
    else:
        strengths[1] /= 2
        return 1

def get_all_more(more, less):
    for i in range(len(more)):
        if more[i] < less[i]:
            return False
    return True

def run_match(red_alliance, blue_alliance, speed, wait, visual, extras):
    
    all_teams = red_alliance + blue_alliance

    prematch_event_strings = []
    postmatch_event_strings = []
    if extras:
        for team in all_teams:
            if team.robot_health == 1:
                event_type = globals()[constants.give_prematch_event()]
                prematch_event_strings.append(str(event_type(team)))
            else:
                prematch_event_strings.append(str(Repair(team)))

    red_strengths = [team.give_score() for team in red_alliance]

    blue_strengths = [team.give_score() for team in blue_alliance]

    red_score_gen = int(sum(red_strengths) / 2)
    blue_score_gen = int(sum(blue_strengths) / 2)

    #0 = orange, 1 = green, 2 = purple
    red_focus_cube = random.randint(0, 2)
    blue_focus_cube = random.randint(0, 2)

    towers_pred = [0, 0, 0]
    red_stacks_pred = [-1, 0, 0]
    blue_stacks_pred = [-1, 0, 0]

    attempts = 0

    while not get_valid_match(towers_pred, red_stacks_pred, blue_stacks_pred):
        if attempts == 10: #Score may be impossible?
            blue_score_gen -= 1
        if attempts == 20:
            red_score_gen -= 1
            attempts = 0
        towers_pred = gen_towers(red_focus_cube, blue_focus_cube)
        red_stacks_pred = gen_stacks(towers_pred, red_focus_cube, red_score_gen)
        blue_stacks_pred = gen_stacks(towers_pred, blue_focus_cube, blue_score_gen)

    #Calculate auton bonus
    red_auton_odds = red_alliance[0].auton_rate + red_alliance[1].auton_rate
    blue_auton_odds = blue_alliance[0].auton_rate + blue_alliance[1].auton_rate
    tie_auton_odds = 0.6 - abs(red_auton_odds - blue_auton_odds) / 2
    #print(red_auton_odds + blue_auton_odds + tie_auton_odds)
    auton_result_num = random.uniform(0, red_auton_odds + blue_auton_odds + tie_auton_odds)
    #print(auton_result_num)
    auton_winner = -1
    if auton_result_num < red_auton_odds:
        auton_winner = 0
    elif auton_result_num < red_auton_odds + blue_auton_odds:
        auton_winner = 1
    else:
        auton_winner = 2

    events = []
    match_totals = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]

    red_auton_result = [0, 0, 0]
    blue_auton_result = [0, 0, 0]

    red_p_auton = None
    red_u_auton = None
    blue_p_auton = None
    blue_u_auton = None

    #Auton generation
    p_autons = [[0, 0, 0], [0], [0, 2, 0, 0]] #Autons common for protected zone (red)
    u_autons = [[0, 2, 1, 2, 1, 1, 0], [0, 2, 1, 1, 0], [0, 2, 1, 1, 0, 2], [0, 2, 1, 1, 0, 0], [0]] #Autons common for unprotected zone (red)

    successful_auton_gen = False
    
    while not successful_auton_gen:

        red_auton_result = [0, 0, 0]
        blue_auton_result = [0, 0, 0]

        red_p = list.copy(random.choice(p_autons))
        red_u = list.copy(random.choice(u_autons))
        blue_p = list.copy(random.choice(p_autons))
        blue_u = list.copy(random.choice(u_autons))

        for i in range(len(blue_p)):
            if blue_p[i] == 0:
                blue_p[i] = 1
            elif blue_p[i] == 1:
                blue_p[i] = 0
        for i in range(len(blue_u)):
            if blue_u[i] == 0:
                blue_u[i] = 1
            elif blue_u[i] == 1:
                blue_u[i] = 0

        fails = [False, False, False, False]

        for i in range(4):
            if random.random() > 0.8:
                fails[i] = True

        red_autons = [red_p, red_u]
        blue_autons = [blue_p, blue_u]

        for i in range(2):
            if not fails[i]:
                for cube in red_autons[i]:
                    red_auton_result[cube] += 1
            if not fails[i + 2]:
                for cube in blue_autons[i]:
                    blue_auton_result[cube] += 1

        red_total = sum(red_auton_result)
        blue_total = sum(blue_auton_result)

        if (red_total > blue_total and auton_winner == 0) or (red_total < blue_total and auton_winner == 1) or (red_total == blue_total and auton_winner == 2): #We randomly picked right
            
            red_p_auton = Stack(1, random.randint(10, 14), red_alliance[0], 0, cube_order=red_p, autofail=fails[0])
            red_u_auton = Stack(0, random.randint(10, 14), red_alliance[1], 0, cube_order=red_u, autofail=fails[1])
            blue_p_auton = Stack(1, random.randint(10, 14), blue_alliance[0], 1, cube_order=blue_p, autofail=fails[2])
            blue_u_auton = Stack(0, random.randint(10, 14), blue_alliance[1], 1, cube_order=blue_u, autofail=fails[3])

            events = [red_p_auton, red_u_auton, blue_p_auton, blue_u_auton]

            successful_auton_gen = True
            
    #Stack event generation

    #Remove auton stacks as necessary (or cuz we feel like it)
    red_available_spots = 3
    blue_available_spots = 3
    destacks = []

    red_spot_list = [0, 1, 2]
    blue_spot_list = [0, 1, 2]

    red_still_needed = [red_stacks_pred[i] - red_auton_result[i] for i in range(3)]
    blue_still_needed = [blue_stacks_pred[i] - blue_auton_result[i] for i in range(3)]

    stack_size_reasonable = False

    while not stack_size_reasonable:
        red_available_spots = 3
        blue_available_spots = 3
        destacks = []

        red_spot_list = [0, 1, 2]
        blue_spot_list = [0, 1, 2]

        red_still_needed = [red_stacks_pred[i] - red_auton_result[i] for i in range(3)]
        blue_still_needed = [blue_stacks_pred[i] - blue_auton_result[i] for i in range(3)]
        for event in events:
            if type(event) == Stack and not event.autofail:
                if event.color == 0: 
                    if not get_all_more(red_stacks_pred, red_auton_result) or random.random() < 0.5:
                        destacks.append(Destack(event, random.randint(16, 25)))
                        for i in range(3):
                            red_auton_result[i] -= event.cube_totals[i]
                    else:
                        red_spot_list.remove(event.location)
                        red_available_spots -= 1
                if event.color == 1:
                    if not get_all_more(blue_stacks_pred, blue_auton_result) or random.random() < 0.5:
                        destacks.append(Destack(event, random.randint(16, 25)))
                        for i in range(3):
                            blue_auton_result[i] -= event.cube_totals[i]
                    else:
                        blue_spot_list.remove(event.location)
                        blue_available_spots -= 1
        if sum(red_still_needed) <= red_available_spots * 12 and sum(blue_still_needed) <= blue_available_spots * 12:
            stack_size_reasonable = True
    
    for event in destacks:
        events.append(event)

    red_still_needed = [red_stacks_pred[i] - red_auton_result[i] for i in range(3)]
    blue_still_needed = [blue_stacks_pred[i] - blue_auton_result[i] for i in range(3)]

    #Generate stacks to add
    try:
        red_stacks = [[0, 0, 0] for i in range(random.randint(int(sum(red_still_needed) / 12) + 1, red_available_spots))]
    except ValueError:
        red_stacks = [[0, 0, 0] for i in range(red_available_spots)]

    try:
        blue_stacks = [[0, 0, 0] for i in range(random.randint(int(sum(blue_still_needed) / 12) + 1, blue_available_spots))]
    except ValueError:
        blue_stacks = [[0, 0, 0] for i in range(blue_available_spots)]

    for i in range(3):
        for j in range(red_still_needed[i]):
            red_stacks[random.randint(0, len(red_stacks) - 1)][i] += 1
        for j in range(blue_still_needed[i]):
            blue_stacks[random.randint(0, len(blue_stacks) - 1)][i] += 1

    for stack in red_stacks:
        location = random.choice(red_spot_list)
        if location == 2 and (1 in red_spot_list):
            location = 1
        events.append(Stack(location, random.randint(30, 120), red_alliance[pick_acting_team(red_strengths)], 0, cube_totals=stack))
        red_spot_list.remove(location)
    for stack in blue_stacks:
        location = random.choice(blue_spot_list)
        if location == 2 and (1 in blue_spot_list):
            location = 1
        events.append(Stack(location, random.randint(30, 120), blue_alliance[pick_acting_team(blue_strengths)], 1, cube_totals=stack))
        blue_spot_list.remove(location)

    #Generate tower event times
    tower_times = []
    for i in range(sum(towers_pred)):
        tower_times.append(random.randint(45, 120))
    tower_times.sort()

    #Quietly sim to determine what alliance should put each tower

    red_sim_results = [0, 0, 0]
    blue_sim_results = [0, 0, 0]
    events.sort(key=lambda x: x.time)
    tower_events = []
    curr_event = 0
    free_towers = [0, 1, 2, 3, 4, 5, 6]
    tower_colors_needed = []
    for i in range(3):
        for j in range(towers_pred[i]):
            tower_colors_needed.append(i)


    for time in range(0, 120):
        if curr_event < len(events) and events[curr_event].time == time:
            while curr_event < len(events) and events[curr_event].time == time:
                event = events[curr_event]
                if type(event) == Stack:
                    if event.color == 0:
                        for i in range(3):
                            red_sim_results[i] += event.cube_totals[i]
                    else:
                        for i in range(3):
                            blue_sim_results[i] += event.cube_totals[i]
                elif type(event) == Destack:
                    if event.color == 0:
                        for i in range(3):
                            red_sim_results[i] -= event.cube_totals[i]
                    else:
                        for i in range(3):
                            blue_sim_results[i] -= event.cube_totals[i]
                curr_event += 1
        if len(tower_times) == 0:
            break
        if tower_times[0] == time:
            tower_color = tower_colors_needed.pop(random.randint(0, len(tower_colors_needed) - 1))
            if red_sim_results[tower_color] > blue_sim_results[tower_color]:
                tower_team = 0
            elif red_sim_results[tower_color] < blue_sim_results[tower_color]:
                tower_team = 1
            else:
                tower_team = random.randint(0, 1)
            valid_tower = False
            tower_loc = 7
            while not valid_tower:
                tower_loc = random.choice(free_towers)
                if not ((tower_team == 0 and tower_loc == 6) or (tower_team == 1 and tower_loc == 0)):
                    valid_tower = True
                    free_towers.remove(tower_loc)
            if tower_team == 0:
                tower_events.append(Tower(tower_loc, tower_color, time, red_alliance[pick_acting_team(red_strengths)], 0))
            else:
                tower_events.append(Tower(tower_loc, tower_color, time, blue_alliance[pick_acting_team(blue_strengths)], 1))
            del tower_times[0]
    
    for event in tower_events:
        events.append(event)
    
    #Add special events:
    #Defense:
    for i in range(3):
        if random.random() < constants.DEFENSE_ODDS:
            acting_alliance = random.randint(0, 1)
            try:
                if acting_alliance == 0:
                    if random.randint(1, sum(red_alliance[0].scores) + sum(red_alliance[1].scores)) < sum(red_alliance[0].scores):
                        defender = red_alliance[1]
                    else:
                        defender = red_alliance[0]
                    if random.randint(1, sum(blue_alliance[0].scores) + sum(blue_alliance[1].scores)) < sum(blue_alliance[0].scores):
                        recipient = blue_alliance[0]
                    else:
                        recipient = blue_alliance[1]
                else:
                    if random.randint(1, sum(blue_alliance[0].scores) + sum(blue_alliance[1].scores)) < sum(blue_alliance[0].scores):
                        defender = blue_alliance[1]
                    else:
                        defender = blue_alliance[0]
                    if random.randint(1, sum(red_alliance[0].scores) + sum(red_alliance[1].scores)) < sum(red_alliance[0].scores):
                        recipient = red_alliance[0]
                    else:
                        recipient = red_alliance[1]
            except ValueError:
                if acting_alliance == 0:
                    defender = random.choice(red_alliance)
                    recipient = random.choice(blue_alliance)
                else:
                    defender = random.choice(blue_alliance)
                    recipient = random.choice(red_alliance)
            questionable = False
            if random.random() < constants.DEFENSE_DQ_ODDS:
                questionable = True
                if random.random() < constants.DQ_CARRY_THROUGH_ODDS:
                    postmatch_event_strings.append(defender.name + " has been issued a DQ!")
            events.append(Defense(15 + (i + 1) * random.randint(1, 35), defender, acting_alliance, recipient, events, questionable))
            for j in range(i + 1, 3):
                if random.random() < constants.DEFENSE_CONTINUE_ODDS:
                    questionable = False
                    if random.random() < constants.DEFENSE_DQ_ODDS:
                        questionable = True
                        if random.random() < constants.DQ_CARRY_THROUGH_ODDS:
                            postmatch_event_strings.append(defender.name + " has been issued a DQ for defense on " + recipient.name + "!")
                    events.append(Defense(15 + (i + 1) * random.randint(1, 35), defender, acting_alliance, recipient, events, questionable))

    #Damage during match:
    damaged_teams = []
    if random.random() < constants.DAMAGE_ODDS:
        damaged_alliance = random.randint(0, 1)
        if damaged_alliance == 0:
            damaged_team = random.choice(red_alliance)
        else:
            damaged_team = random.choice(blue_alliance)
        damager = None
        if random.random() < constants.DAMAGE_INTENTION_ODDS:
            if damaged_alliance == 0:
                damager = random.choice(blue_alliance)
            else:
                damager = random.choice(red_alliance)
            if random.random() < constants.DQ_CARRY_THROUGH_ODDS:
                postmatch_event_strings.append(damager.name + " has been issued a DQ for damaging " + damaged_team.name + "!")
        extent = random.choices(list(constants.DAMAGE_TYPES.keys()), weights=constants.DAMAGE_TYPE_ODDS)[0]
        repair_category = random.choices(list(constants.DAMAGE_LENGTHS.keys()), weights=[0.5, 0.3, 0.2])[0]
        repair_time = random.randint(0, 25) + constants.DAMAGE_LENGTHS[repair_category]
        postmatch_event_strings.append(damaged_team.name + " appears to have sustained " + extent + " damage.")
        postmatch_event_strings.append(repair_category)
        events.append(Damage(random.randint(15, 120), damaged_team, damaged_alliance, extent, repair_time, constants.DAMAGE_TYPES[extent], damager))
    
    events.sort(key=lambda x: x.time)

    #Run match and log events
    curr_event = 0
    auton_winner = -1
    if visual:
        app = QtWidgets.QApplication(sys.argv)
        ui = Ui_MainWindow()
        bot1 = Bot(ui.centralwidget, 0, red_alliance[0].name, 420, 350)
        bot2 = Bot(ui.centralwidget, 0, red_alliance[1].name, 420, 950)
        bot3 = Bot(ui.centralwidget, 1, blue_alliance[0].name, 1670, 350)
        bot4 = Bot(ui.centralwidget, 1, blue_alliance[1].name, 1670, 950)
        ui.align()
        for event in events:
            event.init_visualization(ui.centralwidget)
        ui.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        ui.show()
    os.system('clear')
    if extras:
        for event in prematch_event_strings:
            print(event)
    input("Press enter to begin")
    for time in range(121):
        if visual:
            QtWidgets.QApplication.processEvents()
        if wait:
            sleep(speed)
        if curr_event < len(events) and events[curr_event].time == time:
            while curr_event < len(events) and events[curr_event].time == time:
                update_cubes(match_totals, events[curr_event].act())
                events.sort(key=lambda x: x.time)
                if visual:
                    events[curr_event].visualize(ui)
                curr_event += 1
        if time == 14:
            if sum(match_totals[1]) > sum(match_totals[2]):
                auton_winner = 0
                print(redtext("Red wins autonomous!"))
            elif sum(match_totals[1]) < sum(match_totals[2]):
                auton_winner = 1
                print(bluetext("Blue wins autonomous!"))
            else:
                print("Autonomous tie!")
                auton_winner = 2
            input("Press enter to begin driver control")
    red_final_score = calc_score(match_totals[0], match_totals[1])
    blue_final_score = calc_score(match_totals[0], match_totals[2])
    if auton_winner == 0:
        red_final_score += 6
    elif auton_winner == 1:
        blue_final_score += 6
    else:
        red_final_score += 3
        blue_final_score += 3
    print("Time up!")
    print("Towers: " + cube_totals_to_string(match_totals[0]))
    print("Red stacks: " + cube_totals_to_string(match_totals[1]))
    print("Blue stacks: " + cube_totals_to_string(match_totals[2]))

    print("Final score: " + redtext(red_final_score) + '-' + bluetext(blue_final_score))

    #Damage after match:
    if random.random() < constants.POST_DAMAGE_ODDS:
        damaged_team = random.choice(all_teams)
        extent = random.choices(list(constants.DAMAGE_TYPES.keys()), weights=constants.DAMAGE_TYPE_ODDS)[0]
        damaged_team.robot_health = constants.DAMAGE_TYPES[extent]
        repair_category = random.choices(list(constants.DAMAGE_LENGTHS.keys()), weights=[0.5, 0.3, 0.2])[0]
        damaged_team.repair_time = random.randint(0, 25) + constants.DAMAGE_LENGTHS[repair_category]
        postmatch_event_strings.append(damaged_team.name + " appears to have sustained " + extent + " damage.")
        postmatch_event_strings.append(repair_category)
        damaged_teams.append(damaged_team)

    for team in damaged_teams:
        team.exportJSON()

    for event in postmatch_event_strings:
        print(event)
    input("Press enter to quit")

'''
    for event in events:
        update_cubes(match_totals, event.act())
        #print(match_totals)
'''

    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Simulate a competition match')
    parser.add_argument('red1', help='Red alliance team 1')
    parser.add_argument('red2', help='Red alliance team 2')
    parser.add_argument('blue1', help='Blue alliance team 1')
    parser.add_argument('blue2', help='Blue alliance team 2')
    parser.add_argument('--no-visual', dest='visual', action='store_false', default=True, help='Don\'t run the visualization')
    parser.add_argument('--speed', type=float, default = constants.DEFAULT_SPEED, help='Speed to run the simulation')
    parser.add_argument('--no-wait', dest='wait', action='store_false', default=True, help='Use to run full match immediately without waiting')
    parser.add_argument('--no-extras', dest='extras', action='store_false', default=True, help='Use to bypass prematch and postmatch events')
    args = parser.parse_args()
    try:
        red1 = Team.fromJSON('team_data/' + args.red1 + '.json')
        red2 = Team.fromJSON('team_data/' + args.red2 + '.json')
        blue1 = Team.fromJSON('team_data/' + args.blue1 + '.json')
        blue2 = Team.fromJSON('team_data/' + args.blue2 + '.json')
    except FileNotFoundError as err:
        print("Team file not found for team " + os.path.splitext(os.path.basename(err.filename))[0])
        quit()
    reds = [red1, red2]
    blues = [blue1, blue2]
    ui = None       
    run_match(reds, blues, args.speed, args.wait, args.visual, args.extras)
        #sys.exit(app.exec_())