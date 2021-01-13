import socket, json, os, random
from math import ceil

phone_number = os.environ["SIGNAL_PHONE_NUMBER"]

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect(os.environ["SIGNALD_FILE"])


def render_latex(eq):
    eq = eq.replace("\n", "")
    temp_name = "/tmp/latex_render." + str(random.randint(1, 2**32)) + ".png"
    os.system(
        "timeout 2s pnglatex -m 5 -p \"amsmath,amsfonts,amssymb,mathdots,mathtools,mhchem,stackrel,stmaryrd,xypic\" -e displaymath -d 500 -f " +
        json.dumps(eq) +
        " -o " +
        temp_name)
    return temp_name


def send_signal_data(data):
    sock.send(json.dumps(data).encode("utf-8") + b"\n")


def send_signal_message(
        recipient_address=None,
        recipient_group_id=None,
        reply_message_obj=None,
        body=None,
        attachments=None):
    data = {
        "type": "send",
        "username": phone_number
    }

    if recipient_address is not None:
        data["recipientAddress"] = recipient_address
    if recipient_group_id is not None:
        data["recipientGroupId"] = recipient_group_id
    if reply_message_obj is not None:
        # Support either a group or private dms
        if "syncMessage" in reply_message_obj and \
           "sent" in reply_message_obj["syncMessage"] and \
           "message" in reply_message_obj["syncMessage"]["sent"] and \
           "groupV2" in reply_message_obj["syncMessage"]["sent"]["message"]:
            data["recipientGroupId"] = reply_message_obj["syncMessage"]["sent"]["message"]["groupV2"]["id"]
        else:
            data["recipientAddress"] = {"number": reply_message_obj["username"]}
    if body is not None:
        data["messageBody"] = body
    if attachments is not None:
        data["attachments"] = attachments
    send_signal_data(data)


def got_signal_message(body, source, full_data):
    if body is not None and "body" in body:
        equations = body["body"].split("$$")
        for i in range(1, len(equations), 2):
            eq = equations[i]
            temp_name = render_latex(eq)
            send_signal_message(attachments=[{
                "filename": temp_name
            }], reply_message_obj=full_data)


buff = b""
send_signal_data({"type": "subscribe", "username": phone_number})
while True:
    buff_next = sock.recv(4096)
    newline_index = buff_next.find(b"\n")
    while newline_index != -1:
        until_line = buff + buff_next[:newline_index]
        try:
            data = json.loads(until_line.decode("utf-8"))
        except BaseException:
            pass
        if data["type"] == "message":
            ddata = data["data"]
            try:
                got_signal_message(
                    ddata["syncMessage"]["sent"]["message"]
                    if "syncMessage" in ddata
                    and "sent" in ddata["syncMessage"]
                    and "message" in ddata["syncMessage"]["sent"]
                    else None,
                    ddata["source"],
                    ddata)
            except BaseException as e:
                print(e, type(e))
        buff = b""
        buff_next = buff_next[(newline_index + 1):]
        newline_index = buff_next.find(b"\n")
    buff += buff_next
