# 这些函数主要用于生成各种通知和报告的 HTML 邮件。它们通过读取 HTML 模板文件，并使用传入的数据进行格式化，然后使用 send_html 函数发送邮件。
# 这种方法使得邮件内容的生成非常灵活，并且可以根据需求轻松更改模板或数据。
from chalicelib.utils.TimeUTC import TimeUTC
from chalicelib.utils.email_handler import __get_html_from_file, send_html


# 这个函数用于发送团队邀请邮件。
# 它从 invitation.html 文件中获取模板，并将 invitationLink、clientId 和 sender 作为变量插入。
# 邮件主题是 "Welcome to OpenReplay"，并发送给指定的收件人。
def send_team_invitation(recipient, client_id, sender_name, invitation_link):
    BODY_HTML = __get_html_from_file("chalicelib/utils/html/invitation.html", formatting_variables={"invitationLink": invitation_link, "clientId": client_id, "sender": sender_name})
    SUBJECT = "Welcome to OpenReplay"
    send_html(BODY_HTML, SUBJECT, recipient)

# 这个函数用于发送忘记密码的恢复邮件。
# 它从 reset_password.html 文件中获取模板，并插入 invitationLink 变量。
# 邮件主题是 "Password recovery"，并发送给指定的收件人。
def send_forgot_password(recipient, invitation_link):
    BODY_HTML = __get_html_from_file("chalicelib/utils/html/reset_password.html", formatting_variables={"invitationLink": invitation_link})
    SUBJECT = "Password recovery"
    send_html(BODY_HTML, SUBJECT, recipient)

# 这个函数用于发送会话分配的通知邮件。
# 它从 assignment.html 文件中获取模板，并插入 message、当前时间 now 和 link 变量。
# 邮件主题是 "assigned session"，并发送给指定的收件人。
def send_assign_session(recipient, message, link):
    BODY_HTML = __get_html_from_file("chalicelib/utils/html/assignment.html", formatting_variables={"message": message, "now": TimeUTC.to_human_readable(TimeUTC.now()), "link": link})
    SUBJECT = "assigned session"
    send_html(BODY_HTML, SUBJECT, recipient)

# 这个函数用于发送警告通知邮件。
# 它从 alert_notification.html 文件中获取模板，并插入 data 字典中的变量。
# 邮件主题是传入的 subject，并发送给指定的收件人。
def alert_email(recipients, subject, data):
    BODY_HTML = __get_html_from_file("chalicelib/utils/html/alert_notification.html", formatting_variables=data)
    send_html(BODY_HTML=BODY_HTML, SUBJECT=subject, recipient=recipients)

# 这是一个私有函数，用于根据索引返回不同的颜色值。
# 通常用于在生成报告时为不同类型的条目赋予不同的颜色。
def __get_color(idx):
    return "#3EAAAF" if idx == 0 else "#77C3C7" if idx == 1 else "#9ED4D7" if idx == 2 else "#99d59a"

# 这个函数用于生成并发送项目的每周报告邮件。
# 它使用传入的 data 生成报告内容，包括图表、趋势图等。
# __get_color 函数被用于为不同类型的数据生成颜色。
# 最终的 HTML 内容从 Project-Weekly-Report.html 文件中获取，并通过插入 data 中的变量进行格式化。
# 邮件主题是 "OpenReplay Project Weekly Report"，并发送给指定的收件人。
def weekly_report2(recipients, data):
    data["o_tr_u"] = ""
    data["o_tr_d"] = ""
    for d in data["days_partition"]:
        data[
            "o_tr_u"
        ] += f"""<td valign="bottom" style="padding:0 5px 0 0;width:14%;font-weight:300;margin:0;text-align:left">
                    <table style="width:100%;font-weight:300;margin-bottom:0;border-collapse:collapse">
                        <tbody>
                        <tr style="font-weight:300">
                          <td height="{d["value"]}px" title="{d["issues_count"]}" style="font-size:0;padding:0;font-weight:300;margin:0;line-height:0;background-color:#C5E5E7;text-align:left">&nbsp;</td>
                        </tr>
                    </tbody></table>
                  </td>"""
        data["o_tr_d"] += f"""<td title="{d["day_long"]}, midnight" style="font-size:10px;color:#333333;padding:3px 5px 0 0;width:14%;font-weight:300;margin:0;text-align:center">{d["day_short"]}</td>"""

    data["past_week_issues_status"] = f'<img src="img/weekly/arrow-{"increase" if data["past_week_issues_evolution"] > 0 else "decrease"}.png" width="15px" height="10px" style="font-weight:300;vertical-align:middle">'
    data["week_decision"] = "More" if data["past_week_issues_evolution"] > 0 else "Fewer"
    data["past_week_issues_evolution"] = abs(data["past_week_issues_evolution"])
    data["past_month_issues_status"] = f'<img src="img/weekly/arrow-{"increase" if data["past_month_issues_evolution"] > 0 else "decrease"}.png" width="15px" height="10px" style="font-weight:300;vertical-align:middle">'
    data["month_decision"] = "More" if data["past_month_issues_evolution"] > 0 else "Fewer"
    data["past_month_issues_evolution"] = abs(data["past_month_issues_evolution"])
    data["progress_legend"] = []
    data["progress_tr"] = ""
    for idx, i in enumerate(data["issues_by_type"]):
        color = __get_color(idx)
        data["progress_legend"].append(
            f"""<td style="padding:0;font-weight:300;margin:0;text-align:left;">
                    <span style="white-space:nowrap;"><span style="border-radius:50%;font-weight:300;vertical-align:bottom;color:#fff;width:16px;height:16px;margin:0 8px;display:inline-block;background-color:{color}"></span>{i["count"]}</span><span style="font-weight:300;margin-left:5px;margin-right:0px;white-space:nowrap;">{i["type"]}</span>
                </td>"""
        )
        data["progress_tr"] += f'<td width="{i["value"]}%" title="{i["count"]} {i["type"]}" style="padding:0;font-weight:300;margin:0;background-color:{color};text-align:left">&nbsp;</td>'

    data["progress_legend"] = '<tr style="font-weight:300;font-size:13px;">' + "".join(data["progress_legend"]) + "</tr>"
    data["breakdown_list"] = ""
    color_breakdown = {}
    data["breakdown_list_other"] = ""
    # enumerate 是 Python 内置函数之一，它在遍历列表、元组或其他可迭代对象时为每个元素提供一个索引，
    # 生成一个由索引和值组成的元组。enumerate 非常有用，当你在遍历可迭代对象时，需要同时获取元素的索引和元素本身时。
    for idx, i in enumerate(data["issues_breakdown_list"]):
        if idx < len(data["issues_breakdown_list"]) - 1 or i["type"].lower() != "others":
            color = __get_color(idx)
            color_breakdown[i["type"]] = color
            data[
                "breakdown_list"
            ] += f"""<tr style="font-weight:300">
              <td style="font-size:14px;padding:5px 0;font-weight:300;margin:0;text-align:left;white-space:nowrap;"><span style="vertical-align: middle;border-radius:50%;width:1em;font-weight:300;display:inline-block;background-color:{color};height:1em"></span>&nbsp;&nbsp;{i["type"]}</td>
              <td style="font-size:14px;padding:5px 0;font-weight:300;margin:0;text-align:left"><a href="%(frontend_url)s" style="color:#394EFF;font-weight:300;text-decoration:none" target="_blank" data-saferedirecturl="#">{i["sessions_count"]}</a></td>
              <td style="font-size:14px;padding:5px 0;font-weight:300;margin:0;text-align:left"><img src="img/weekly/arrow-{"increase" if i["last_week_sessions_evolution"] > 0 else "decrease"}.png" width="10px" height="7px" style="font-weight:300;vertical-align:middle;margin-right: 3px;"> {abs(i["last_week_sessions_evolution"])}%</td>
              <td style="font-size:14px;padding:5px 0;font-weight:300;margin:0;text-align:left"><img src="img/weekly/arrow-{"increase" if i["last_month_sessions_evolution"] > 0 else "decrease"}.png" width="10px" height="7px" style="font-weight:300;vertical-align:middle;margin-right: 3px;"> {abs(i["last_month_sessions_evolution"])}%</td>
            </tr>"""
        else:
            data[
                "breakdown_list_other"
            ] = f"""<tfoot style="font-weight:300">
            <tr style="font-weight:300">
              <td style="font-size:14px;padding:5px 0;font-weight:300;margin:0;text-align:left;white-space:nowrap;"><span style="vertical-align: middle;border-radius:50%;width:1em;font-weight:300;display:inline-block;background-color:#999999;height:1em"></span>&nbsp;&nbsp;{i["type"]}</td>
              <td style="font-size:14px;padding:5px 0;font-weight:300;margin:0;text-align:left"><a href="%(frontend_url)s" style="color:#394EFF;font-weight:300;text-decoration:none" target="_blank" data-saferedirecturl="#">{i["sessions_count"]}</a></td>
              <td style="font-size:14px;padding:5px 0;font-weight:300;margin:0;text-align:left"><img src="img/weekly/arrow-{"increase" if i["last_week_sessions_evolution"] > 0 else "decrease"}.png" width="10px" height="7px" style="font-weight:300;vertical-align:middle;margin-right: 3px;"> {abs(i["last_week_sessions_evolution"])}%</td>
              <td style="font-size:14px;padding:5px 0;font-weight:300;margin:0;text-align:left"><img src="img/weekly/arrow-{"increase" if i["last_month_sessions_evolution"] > 0 else "decrease"}.png" width="10px" height="7px" style="font-weight:300;vertical-align:middle;margin-right: 3px;"> {abs(i["last_month_sessions_evolution"])}%</td>
            </tr>
        </tfoot>"""
    data["b_tr_u"] = ""
    data["b_tr_d"] = ""
    for i in data["issues_breakdown_by_day"]:
        data[
            "b_tr_d"
        ] += f"""<td title="{i["day_long"]}" style="font-size:14px;color:#333333;padding:10px 0 0;width:14%;border-right:10px solid #fff;font-weight:300;margin:0;text-align:center">
            {i["day_short"]}
          </td>"""
        if len(i["partition"]) > 0:
            sup_partition = ""
            for j in i["partition"]:
                sup_partition += f'<tr style="font-weight:300"><td height="{j["value"]}" title="{j["count"]} {j["type"]}" style="font-size:0;padding:0;border-right:none;font-weight:300;margin:0;line-height:0;background-color:{color_breakdown[j["type"]]};text-align:left"></td></tr>'
        else:
            sup_partition = '<tr style="font-weight:300"><td height="3" style="font-size:0;padding:0;border-right:none;font-weight:300;margin:0;line-height:0;background-color:#999999;text-align:left"></td></tr>'
        data[
            "b_tr_u"
        ] += f"""<td valign="bottom" style="font-size:0;font-weight:300;padding:0;width:14%;border-right:10px solid #fff;height:110px;margin:0;text-align:left">
            <table style="width:100%;font-weight:300;margin-bottom:0;border-collapse:collapse">
                <tbody>{sup_partition}</tbody>
            </table>
          </td>"""
    BODY_HTML = __get_html_from_file("chalicelib/utils/html/Project-Weekly-Report.html", formatting_variables=data)
    SUBJECT = "OpenReplay Project Weekly Report"
    send_html(BODY_HTML=BODY_HTML, SUBJECT=SUBJECT, recipient=recipients)
