# import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
# Image, Paragraph,
# from reportlab.lib.styles import getSampleStyleSheet
from openpyxl import Workbook


# def create_table(db, start_day, days_amount, shift_time):
def db_table(db, dates, shifts):
    # doc = SimpleDocTemplate("schedule.pdf", pagesize=letter)
    # elements = []
    data = []
    schedule = db.execute(
            'SELECT s.id, shift, date, created, author_id, username'
            ' FROM schedule s JOIN user u ON s.author_id = u.id'
            ' ORDER BY created DESC'
        ).fetchall()
    
    for line in schedule:
        row = []
        for date in dates:
            for shift in shifts:
                if line['date'] == date and line['shift'] == shift:
                    row.append(line['username'])
                else:
                    row.append("")
                data.append(row)
    return None


def web_table(html, table_number=1, debug=True):
    """ creates a table of content using the html page given """
    if debug:
        with open("ta.txt", "w") as f:
            f.write(html)
        f.close()

    dates = []
    shifts = []
    table = []
    table_number = 1 if table_number == 0 else table_number
    t = html.split('<table class="container2">')[table_number].split('<div id="add_pop"')[0]

    temp = t.split("<h1>")[2:]
    for one in temp:
        dates.append(one.split("</h1>")[0].replace("\r\n", "\n"))

    temps = t.split('<td class="shift" style="text-align: center;">')[1:]  # fix
    for one in temps:
        shifts.append(one.split("</td>")[0].replace(" -", ":00 -") + ":00")

    div = t.split('<td class="square')[1:]
    for one in div:
        row = []
        tempp = one.split("<p")[1: -1]
        for i in tempp:
            row.append(i.split(">")[1].split("</p")[0])
        if row != []:
            table.append('\n'.join(row))
        else:
            table.append(' '.join(row))

    rows = []
    line = []
    for i, item in enumerate(table):
        if i != 0 and i % len(dates) == 0:
            rows.append(line)
            line = [item]
        else:
            line.append(item)
    rows.append(line)

    table = []
    temp = [" "]
    temp.extend(dates)
    table.append(temp)
    print table
    for i in xrange(len(shifts)):
        r = [shifts[i]]
        r.extend(rows[i])
        table.append(r)
    for l in table:
        print l
    return table


def create_table(data):
    """ creates a pdf with a table using the data provided """
    doc = SimpleDocTemplate("table.pdf", pagesize=A4[::-1])
    elements = []
    t = Table(data)
    t.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'RIGHT'),
                           ('TEXTCOLOR', (1, 1), (-1, -1), colors.red),
                           ('VALIGN', (0, 0), (0, -1), 'TOP'),
                           ('TEXTCOLOR', (0, 0), (0, -1), colors.blue),
                           ('ALIGN', (0, -1), (-1, -1), 'CENTER'),
                           ('VALIGN', (0, -1), (-1, -1), 'MIDDLE'),
                           ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                           ('BOX', (0, 0), (-1, -1), 0.25, colors.black)]))
    elements.append(t)
    doc.build(elements)


def create_excel_table(data):
    wb = Workbook()
    ws = wb.active

    days = data[0]
    for i in xrange(len(days)):
        ws["{}1".format(chr(ord('A') + i))] = days[i]

    for line in data[1:]:
        for i in xrange(len(line)):
            # line[i] = line[i].replace("\n", "CHAR(10)")
            if line[i].count("\n") > 0:
                if line[i][0] == "\n":
                    line[i] = line[i].replace("\n", "")
                else:
                    line[i] = '="' + '" & CHAR(10) & "'.join(line[i].split("\n")) + '"'
        ws.append(line)

    for i in xrange(8):
        for j in xrange(len(data) + 1):
            ws.row_dimensions[j].height = 40
            ws.column_dimensions[chr(ord('A') + i)].width = 30

    wb.save('{}.xlsx'.format('table'))


# create a costume table
class User(object):
    def __init__(self, name):
        self.username = name
        self.done_night = False
        self.hour_in_shift = 8
        self.shifts = []

    def add_shift(self, start, end, night=False):
        if self.shifts is []:
            self.shifts.append([start, end])
        elif self.shifts[-1][1] + self.hour_in_shift <= start and not self.done_night and night:
            self.shifts.append([start, end])
            self.done_night = True
        else:
            return "error - %s has a night shift before hand or the shifts are not in an 8 hour apart" % self.username
