salary_cap_2016 = 94 * 1000000
luxury_tax_2016 = 84.74 * 1000000

salary_cap_2017 = 102 * 1000000
luxury_tax_2017 = 113.287 * 1000000

salary_cap_2018 = 108 * 1000000

nonrepeater_list1 = [(luxury_tax_2017, 0), (5000000, 1.5), (5000000, 1.75), (5000000, 2.5), (5000000, 3.25),
                     (5000000, 3.75), (5000000, 4.25), (5000000, 4.75)]
repeater_list1 = [(luxury_tax_2017, 0), (5000000, 2.5), (5000000, 2.75), (5000000, 3.5), (5000000, 4.25),
                  (5000000, 4.75), (5000000, 5.25), (5000000, 5.75)]


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


def get_bill_with_taxes(salaries, repeater=False):
    return salaries + get_taxes(salaries, repeater=repeater)


def calculate_max_salary(maxi, max_years=5, jump=1.075, salary=0, year=1):
    if year > max_years:
        return salary
    else:
        salary += maxi * pow(jump, (year - 1))
        return calculate_max_salary(maxi, max_years, jump, salary, year + 1)

cavs_salaries_without_jr = 116.599976 * 1000000
jr_salary = 15 * 1000000


print(get_bill_with_taxes(cavs_salaries_without_jr, repeater=True))
print(get_bill_with_taxes(cavs_salaries_without_jr+jr_salary, repeater=True))
