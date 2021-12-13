import os
import json
import click
# from stat import S_IREAD
from flask.cli import with_appcontext
from logging import basicConfig, getLogger, INFO

FILE_NAME = "log.txt"
LOGS_DIR = "{}\logs".format(os.getcwd())
LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"


def get_logger(file_name=FILE_NAME, debug_level=INFO):
    """ creates a logger variable using the variables provided and returns it """
    basicConfig(filename=file_name, level=debug_level, format=LOG_FORMAT)
    return getLogger()


@click.command('init-log')
@with_appcontext
def init_log_command():
    """ Clear the existing data from the log file. """
    with open(FILE_NAME, "r") as f:
        read = f.read()
    f.close()

    with open("log_backup.txt", "w") as f:
        f.write(read)
    f.close()

    f = open(FILE_NAME, "w")
    f.close()
    # os.chmod(FILE_NAME, S_IREAD)  # read only mode
    click.echo('Initialized  the log file')


def remove_errors(read):
    """ remove errors from the read variables
        :param read: the log file content """
    div = read.split("Exception on")
    for i in xrange(len(div)):
        if div[i].count("Error") > 0:
            temp = "\n".join(div[i].split("Error: ")[1].split("\n")[1:])
            div[i] = temp
        elif div[i].count("Schema: ") > 0:
            temp = "\n".join(div[i].split("Schema: ")[1].split("\n")[1:])
            div[i] = temp

    return "\n".join(div)


def get_errors(read, to_db=True):
    """ list of all the errors from the read variables
        :param read: the log file content
        :param to_db: if False than the type on each item in the list is text, otherwise the type is json """
    err = []
    div = read.split("ERROR ")
    for item in div:
        if item.count("Error: ") > 0:
            temp = item.split("Error: ")
            full_error = "ERROR " + temp[0] + "Error: " + temp[1].split("\n")[0]
        elif item.count("Schema: ") > 0:
            temp = item.split("Schema: ")
            full_error = "ERROR " + temp[0] + "Schema: " + temp[1].split("\n")[0]
        else:
            continue
        if to_db:
            error = full_error.split("\n")[0].split(" ")
            variables = {
                "level": error[0],
                "date": error[1],
                "time": error[2],
                "error_body": "\n".join(full_error.split("\n")[1:-1]),
                "value": full_error.split("\n")[-1],
                "url": error[6],
                "request_type": error[7][1:-1]
            }
            err.append(variables)
        else:
            err.append(full_error)
    return err


def handle_log_file(separated=True, file_content=None, del_errors=True):
    """ create a list from the log file
        :var separated: if True than the text will be only separated by \n and will stay in it current form
                        otherwise the function will transfer each line into dictionary """

    if file_content is None:
        with open(FILE_NAME, "r") as f:
            read = f.read()
        f.close()
    else:
        read = file_content

    if del_errors:  # handle errors
        read = remove_errors(read)

    if separated:
        return read.split("\n")[:-1]

    # break lines
    lines = read.split("\n")[:-1]
    log = []

    for i in xrange(len(lines)):
        parts = lines[i].split(" ")

        # start line
        if "*" in parts:
            variables = {
                "level": parts[0],
                "date": parts[1],
                "time": parts[2],
                "host": "{} {} {}".format(parts[6], parts[7], parts[8])
            }

        elif parts[0] == "ERROR":
            variables = {
                "level": parts[0],
                "date": parts[1],
                "time": parts[2]
            }

        # debug lines
        elif len(parts) > 5 and "{" in parts[4] and "}" in parts[-1]:
            variables = json.loads("{" + lines[i].split("{")[1])
            variables["level"] = parts[0]
            variables["date"] = parts[1]
            variables["time"] = parts[2]
            variables["type"] = "debug"

        # https get / post requests
        elif '"GET' in parts or '"POST' in parts:
            parts = list(filter(lambda x: x != "-" and x != "", parts))
            response_code_types = {200: "OK", 201: "Created", 202: "Accepted", 203: "Non-Authoritative Information",
                                   204: "No Content", 205: "Reset Content", 206: "Partial Content",
                                   300: "Multiple Choice", 301: "Moved Permanently", 302: "Found", 303: "See Other",
                                   304: "Not Modified", 307: "Temporary Redirect", 308: "Permanent Redirect",
                                   400: "Bad Request", 401: "Unauthorized", 402: "Payment Required", 403: "Forbidden",
                                   404: "Not Found", 405: "Method Not Allowed", 406: "Not Acceptable",
                                   500: "Internal Server Error", 501: "Not Implemented", 502: "Bad Gateway",
                                   503: "Service Unavailable", 504: "Gateway Timeout"}
            variables = {
                "level": parts[0],
                "date": parts[1],
                "time": parts[2],
                "ip": parts[3],
                "user_time": "{} - {}".format(parts[4][1:], parts[5][:-1]),
                "request_type": parts[6][1:],
                "url": parts[7],
                "response_code": "{} - {}".format(parts[-1], response_code_types[int(parts[-1])]),
                "type": "info"
            }

        else:
            continue

        log.append(variables)

    return log


def create_log_file_dir(action="sections", write_type="json"):
    """ create log files directory according to the action provided
        :var action: dates -> for reach day there will be a new log file
                     sections -> for each section such as 'security' / 'errors' etc.
                     there will be a separate log file """

    def backdate(method="text", handle=False):
        """ backdate all the days from the log file into separate files according to there date
            :var method: the type for each line in the new file -> text or json
            :var handle: True will remove what the program read and inserted, False do nothing to the original log file
            note: the assumption is that what is writen in the log file didn't got logged to a separate file """
        dates = {}
        if method == "text":
            log_db = handle_log_file(True)
            error_db = get_errors(open(FILE_NAME, "r").read(), False)
        elif method == "json":
            log_db = handle_log_file(False)
            error_db = get_errors(open(FILE_NAME, "r").read(), True)
        else:
            print "error in method variable"
            return None

        index = 0
        for line in log_db:
            if method == "json":
                date = line["date"]
                time = line["time"]
            else:
                date = line.split(" ")[1]
                time = line.split(" ")[2]

            if index < len(error_db):
                if method == "text" and time == error_db[index].split("\n")[0].split(" ")[2] and \
                                date == error_db[index].split("\n")[0].split(" ")[1]:
                    line = error_db[index]
                    index += 1
                elif method == "json" and time == error_db[index]["time"] and date == error_db[index]["date"]:
                    line = error_db[index]
                    index += 1

            if method == "json":
                line = json.dumps(line)

            if date not in dates.keys():
                if method == "json":
                    dates[date] = [line]
                else:
                    dates[date] = line
            else:
                if method == "json":
                    dates[date].append(line)
                else:
                    dates[date] += "\n{}".format(line)

        for name in dates.keys():
            if method == "json":
                json.dump(dates[name], open("{}\\!{}!.txt".format(LOGS_DIR, name), "w"))
            else:
                with open("{}\\{}.txt".format(LOGS_DIR, name), "w") as f:  # change mode to "a"
                    f.write(dates[name])
                f.close()

        if handle is True:  # remove all log_db data from the log file
            pass

    def divisions(method="text", handle=False):
        """ divide the log file into separate sections that each is on aa different subject
            :var method: the type for each line in the new file -> text or json
            :var handle: True will remove what the program read and inserted, False do nothing to the original log file
            note: the assumption is that what is writen in the log file didn't got logged to a separate file """
        if method == "json":
            log_files = {"Security": [], "Database": [], "Users": [], "Network": []}
        else:
            log_files = {"Security": "", "Database": "", "Users": "", "Network": ""}

        if method == "text":
            log_db = handle_log_file(True)
            error_db = get_errors(open(FILE_NAME, "r").read(), False)
        elif method == "json":
            log_db = handle_log_file(False)
            error_db = get_errors(open(FILE_NAME, "r").read(), True)
        else:
            print "error in method variable - %s" % method
            return None

        if method == "json":
            json.dump(error_db, open("{}\\!Errors!.txt".format(LOGS_DIR), "w"))
        else:
            with open("{}\\Errors.txt".format(LOGS_DIR), "w") as f:  # change mode to "a"
                f.write("\n".join(error_db))
            f.close()

        for line in log_db:
            if method == "text":
                parts = line.split(" ")
                if 'INSERT' in line or 'UPDATE' in line or 'DELETE' in line:
                    log_files["Database"] += "\n{}".format(line)
                if "created_username" in line or "created_id" in line or "Logout" in parts[-1] or "Login" in parts[-1]:
                    log_files["Users"] += "\n{}".format(line)
                if "INIT" in line or "*" in line or (len(parts) > 5 and parts[4].count(".") == 3):
                    log_files["Network"] += "\n{}".format(line)
                if 'warning":' in line or 'info":' in line:
                    log_files["Security"] += "\n{}".format(line)
            elif method == "json":
                if "command" in line.keys() and ("INSERT" in line["command"] or "UPDATE" in line["command"] or
                                                 "DELETE" in line["command"]):
                    log_files["Database"].append(line)
                if "created_username" in line.keys() or "created_id" in line.keys() or \
                   "command" in line.keys() and (line["command"] == "Logout" or line["command"] == "Login"):
                    log_files["Users"].append(line)
                if ("info" in line.keys() and "INIT" in line["info"]) or "host" in line.keys() or "ip" in line.keys():
                    log_files["Network"].append(line)
                if "warning" in line.keys() or "info" in line.keys():
                    log_files["Security"].append(line)
            else:
                print "unknown type - %s" % method

        for name in log_files.keys():
            if method == "json":
                json.dump(log_files[name], open("{}\\!{}!.txt".format(LOGS_DIR, name), "w"))
            else:
                with open("{}\\{}.txt".format(LOGS_DIR, name), "w") as f:  # change mode to "a"
                    if type(log_files[name]) == str:
                        f.write(str(log_files[name])[1:])
                    else:
                        print "error log_files is not str -> %s" % type(log_files[name])
                f.close()

        if handle is True:  # remove all log_db data from the log file
            pass

    try:
        os.mkdir("logs")
    except WindowsError:
        pass

    if action == "dates":
        handle = False
        backdate(method=write_type, handle=handle)

    elif action == "sections":
        # security / errors / db / users / network
        divisions(method=write_type, handle=False)

    else:
        print "error in action value"

    print "done"


def extract_logs(commands, multiple_files=False, div_type=None):
    """ extract the logs according to the commands given
    :param commands: the variables to extract the needed information from the db
    :param multiple_files: if True than the logs will not be from a single log file but from the multiple files
    :param div_type: the type of multiple files: dates / sections """
    text_type = "text"
    if type(commands) == str:
        commands = json.loads(commands)

    if not multiple_files:
        return extract_one_file(commands)
    else:  # Security / Errors / Database / Users / Network
        log_files = ["Security", "Errors", "Database", "Users", "Network"]
        if div_type == "sections":
            if "command" in commands.keys():
                if "INSERT" in commands["command"] or "UPDATE" in commands["command"] or "DELETE" in commands["command"]:
                    if text_type == "json":
                        extract_one_file(commands=commands, db=json.load(open("{}\\Database".format(LOGS_DIR), "r")))
                    else:
                        return extract_one_file(commands=commands,
                                                db=handle_log_file(separated=False, del_errors=False,
                                                                   file_content=open("{}\\Database".format(LOGS_DIR),
                                                                                     "r").read()))
                elif "Logout" in commands["command"] or "Login" in commands["command"]:
                    if text_type == "json":
                        extract_one_file(commands=commands, db=json.load(open("{}\\Users".format(LOGS_DIR), "r")))
                    else:
                        return extract_one_file(commands=commands,
                                                db=handle_log_file(separated=False, del_errors=False,
                                                                   file_content=open("{}\\Users".format(LOGS_DIR),
                                                                                     "r").read()))
                elif "error" in commands["command"]:
                    return extract_one_file(commands=commands, db=get_errors(open(FILE_NAME, "r").read(), True))
                elif "security" in commands["command"]:
                    if text_type == "json":
                        return extract_one_file(commands=commands, db=json.load(open("{}\\Security".format(LOGS_DIR),
                                                                                     "r")))
                    else:
                        return extract_one_file(commands=commands,
                                                db=handle_log_file(separated=False, del_errors=False,
                                                                   file_content=open("{}\\Security".format(LOGS_DIR),
                                                                                     "r").read()))
                else:
                    print "command not found - %s" % commands["command"]
            else:
                if text_type == "json":
                    file_content = []
                    for name in log_files:
                        file_content.append(json.load(open("{}\\{}".format(LOGS_DIR, name), "r")))
                    return extract_one_file(commands=commands, db=file_content)
                else:
                    file_content = ""
                    for name in log_files:  # includes error file
                        file_content += open("{}\\{}".format(LOGS_DIR, name), "r").read()
                    return extract_one_file(commands=commands, db=handle_log_file(separated=False,
                                                                                  file_content=file_content))
        else:  # div_type ==  "dates"
            if text_type == "json":
                file_names = filter(lambda x: x.count("-") and x.count("!"), os.listdir("{}\\logs".format(LOGS_DIR)))
            else:
                file_names = filter(lambda x: x.count("-") and not x.count("!"), os.listdir("{}\\logs".format(LOGS_DIR)))
            if "start_date" in commands.keys() and "end_date" in commands.keys():  # create a list of dates between them
                if text_type == "json":
                    files_content = []
                else:
                    files_content = ""
                start_date = commands["start_date"]
                index = 0
                for name in file_names:
                    day = int(start_date.split("-")[2]) + index
                    date = "{}-{}".format('-'.join(start_date.split("-")[:-1]), "0" + str(day) if day < 10 else day)
                    if date >= commands["end_date"]:
                        break
                    if name.replace("!", "").split(".")[0] == date:
                        if text_type == "json":
                            files_content.append(json.load(open("{}\\{}".format(LOGS_DIR, name), "r")))
                        else:
                            files_content += "{}\n".format(open("{}\\{}".format(LOGS_DIR, name), "r").read())

                if text_type == "json":
                    return extract_one_file(commands=commands, db=files_content)
                else:
                    return extract_one_file(commands=commands, db=handle_log_file(separated=False,
                                                                                  file_content=files_content))


def extract_one_file(commands, db=None):
    """ extract the relevant information according to the commands given
        :var commands: the variables to extract the needed information from the db
        :var db: the information to sort throw """
    print "Commands: {}".format(commands)
    if db is None:
        logs = handle_log_file(False)
    else:
        logs = db

    if len(commands) == 0:
        return db

    if type(commands) == str:
        commands = json.loads(commands)

    new_logs = []
    key = commands.keys()[0]
    skey = ""
    ekey = ""

    value = commands[key]
    evalue = ""

    if "command" in commands.keys() and commands["command"] == "error":
        db = get_errors(open(FILE_NAME, "r").read())
        if key == "command":
            commands.pop("command")
            return extract_one_file(commands, db)
    elif key == "start_time":
        key = "time"
        skey = "start_time"
        ekey = "end_time"
        evalue = commands[ekey]
    elif key == "start_date":
        key = "date"
        skey = "start_date"
        ekey = "end_date"
        evalue = commands[ekey]

    for line in logs:
        try:
            if key == "command" and value == "security" and ("warning" in line.keys() or "info" in line):
                new_logs.append(line)
            elif skey != "" and ekey != "":
                if value <= line[key] <= evalue:
                    new_logs.append(line)
            elif line[key] == value or value in line[key]:
                new_logs.append(line)
        except KeyError:
            pass

    if skey != "" and ekey != "" and evalue != "":
        commands.pop(skey)
        commands.pop(ekey)
    else:
        commands.pop(key)

    return extract_one_file(commands, new_logs)
