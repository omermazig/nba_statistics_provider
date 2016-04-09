luxury_tax = 84.74 * 1000000
nonrepeater_list1 = [(luxury_tax, 0), (5000000, 1.5), (5000000, 1.75), (5000000, 2.5), (5000000, 3.25), (5000000, 3.75), (5000000, 4.25), (5000000, 4.75)]
repeater_list1 = [(luxury_tax, 0), (5000000, 2.5), (5000000, 2.75), (5000000, 3.5), (5000000, 4.25), (5000000, 4.75), (5000000, 5.25), (5000000, 5.75)]

def get_taxes(salaries, repeater=False):
    temp_salaries = salaries
    taxes = 0
    list_to_enumerate = repeater_list1 if repeater else nonrepeater_list1
    for tuple1 in list_to_enumerate:
        if temp_salaries <= tuple1[0]:
            taxes += temp_salaries * tuple1[1]
            break
        else:
            taxes += tuple1[0] * tuple1[1]
            temp_salaries -= tuple1[0]
    return taxes

cavs_salaries = 94.853699 * 1000000
tristan_qo_salary = 6.777589 * 1000000
tristan_salary = 16.407500 * 1000000
jr_salary = 5 * 1000000

print get_taxes(cavs_salaries)
print get_taxes(cavs_salaries + tristan_salary)
print get_taxes(cavs_salaries + tristan_qo_salary)
print get_taxes(cavs_salaries + tristan_qo_salary)


def calculate_max_salary(max_years=5, maxi=16407500, jump=1.075, salary=0, year=1):
    if year > max_years:
        return salary
    else:
        salary += maxi * pow(jump, (year-1))
        return calculate_max_salary(max_years, maxi, jump, salary, year+1)