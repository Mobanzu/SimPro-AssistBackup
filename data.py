import livejson, requests, os, time, json, string, re, random, threading, traceback, sys
from lib.akad import *
from lib.akad.ttypes import TalkException

class commands(threading.Thread):
    def __init__(self, fileName, client, app, uid):
        super(commands, self).__init__()
        self.fileName = fileName
        self.client = client
        self.app = app
        self.uid = uid
        self.db = livejson.File("database/%s.json" %fileName, True, True, 4)
        self.master = ["YOUR_MID"]
        self.invites = []
        self.count = {"countKick": 0, "countInvite": 0, "countCancel": 0}
        self.settings = {
            "protect": {},
            "namelock": {},
            "pictlock": {},
            "linkprotect": {},
            "lockcancel": {},
            "denyinvite": {},
            "autopurge": False,
            "allowban": True,
            "sqmode": True,
            "antibots": False,
            "rname": fileName,
            "sname": "default",
            "restartpoint": None,
            "pictprofile": False,
            "strictmode": {}
        }
        if not "settings" in self.db:
            self.db['settings'] = self.settings
            self.settings = self.db["settings"]
            for oup in self.master:
                client.sendMessage(oup, "Activated.\nMID: %s" %uid)
        else:
            self.settings = self.db["settings"]
        self.stats = {
            "owners": {
                "add": False,
                "del": False,
                "list": []
            },
            "admins": {
                "add": False,
                "del": False,
                "list": []
            },
            "staffs": {
                "add": False,
                "del": False,
                "list": []
            },
            "bots": {
                "add": False,
                "del": False,
                "list": []
            },
            "antijs": {
                "add": False,
                "del": False,
                "list": []
            },
            "banned": {
                "add": False,
                "del": False,
                "list": []
            }
        }
        if not "stats" in self.db:
            self.db['stats'] = self.stats
            self.stats = self.db["stats"]
        else:
            self.stats = self.db["stats"]
        if self.settings["restartpoint"] != None:
            self.client.sendMessage(self.settings["restartpoint"], "Activated")
            self.settings["restartpoint"] = None

    def banned(self, user):
        if user in self.stats["banned"]["list"] or not self.settings["allowban"]: pass
        else: self.stats["banned"]["list"].append(user)
        return 1

    def kicking(self, to, target):
        for a in target:
            try: self.client.kickoutFromGroup(to, [a])
            except: e = traceback.format_exc()

    def canceling(self, to, target):
        for a in target:
            try: self.client.cancelGroupInvitation(to, [a])
            except: e = traceback.format_exc()

    def inviting(self, to, target):
        for a in target:
            try:
                self.client.findAndAddContactsByMid(a)
                self.client.inviteIntoGroup(to, [a])
            except: e = traceback.format_exc()

    def mycmd(self, text, rname, sname):
        cmd = ""
        pesan = text
        if pesan.startswith(rname):
            pesan = pesan.replace(rname, "", 1)
            if " & " in text:
                cmd = pesan.split(" & ")
            else:
                cmd = [pesan]
        if pesan.startswith(sname):
            pesan = pesan.replace(sname, "", 1)
            if " & " in text:
                cmd = pesan.split(" & ")
            else:
                cmd = [pesan]
        return cmd

    def access(self, good):
        u = self.master
        if good in u:
            return 0
        u = self.stats['owners']['list']
        if good in u:
            return 1
        u = self.stats['admins']['list']
        if good in u:
            return 2
        u = self.stats['staffs']['list']
        if good in u:
            return 3
        u = self.stats['bots']['list']
        if good in u:
            return 4
        u = self.stats['antijs']['list']
        if good in u:
            return 5
        return 1000

    def notif_kick_from_group(self, op):
        kickgroup = op.param1
        kicker = op.param2
        kicked = op.param3
        if self.uid == kicked:
            if self.access(kicker) > 5:
                self.banned(kicker)
        elif self.settings["sqmode"] and kicked in self.stats["bots"]["list"]:
            if self.access(kicker) > 5:
                self.kicking(kickgroup, [kicker])
                self.inviting(kickgroup, [kicked])
                self.banned(kicker)
        elif self.access(kicked) < 6:
            if self.access(kicker) > 5:
                self.kicking(kickgroup, [kicker])
                self.inviting(kickgroup, [kicked])
                self.banned(kicker)
        elif kickgroup in self.settings["protect"] and self.access(kicker) > 5:
            self.kicking(kickgroup, [kicker])
            self.banned(kicker)

    def notif_invite_into_group(self, op):
        invites = op.param3.split("\x1e")
        inviter = op.param2
        group = op.param1
        if self.uid in invites:
            if self.access(inviter) < 6:
                self.client.acceptGroupInvitation(group)
        elif group in self.settings["denyinvite"]:
            if self.access(inviter) > 5:
                self.canceling(group, invites)
                self.banned(inviter)
                if self.settings["denyinvite"][group] == 2:
                    self.kicking(group, [inviter])
                    self.invites = invites
        else:
            if not set(self.stats["banned"]["list"]).isdisjoint(invites):
                target = set(self.stats["banned"]["list"]).intersection(invites)
                self.canceling(group, target)
                self.banned(inviter)
                self.invites = invites
                if self.access(inviter) > 5:
                    self.kicking(group, [inviter])
            elif inviter in self.stats["banned"]["list"]:
                self.canceling(group, invites)
                self.kicking(group, [inviter])
                self.invites = invites

    def notif_cancel_invite_group(self, op):
        group = op.param1
        canceler = op.param2
        canceles = op.param3
        if canceles != self.uid:
            if group in self.settings["lockcancel"]:
                if self.access(canceles) < 6:
                    if self.access(canceler) > 5:
                        self.inviting(group, [canceles])
                        self.kicking(group, [canceler])
                        self.banned(canceler)
            elif group in self.settings["denyinvite"]:
                if self.access(canceler) > 5:
                    self.kicking(group, [canceler])
                    self.banned(canceler)

    def notif_update_group(self, op):
        group = op.param1
        changer = op.param2
        if op.param3 == "1":
            if group in self.settings["namelock"]:
                if self.settings["namelock"][group]["on"] == 1:
                    if self.access(changer) > 5:
                        z = self.client.getGroup(group)
                        z.name = self.settings["namelock"][op.param1]["name"]
                        self.client.updateGroup(z)
                        if group in self.settings["protect"]:
                            if self.settings["protect"][group] == 2:
                                self.kicking(group, [changer])
                                self.banned(changer)
            elif group in self.settings["pictlock"]:
                if self.settings["pictlock"][group]["on"] == 1:
                    if self.access(changer) > 5:
                        z = self.client.getGroup(group)
                        z.pictureStatus = self.settings["pictlock"][op.param1]["pict"]
                        pathUrl = "https://obs.line-scdn.net/" + self.settings["pictlock"][op.param1]["pict"]
                        self.client.updateGroupPicture(group, pathUrl)
                        if group in self.settings["protect"]:
                            if self.settings["protect"][group] == 2:
                                self.kicking(group, [changer])
                                self.banned(changer)
        else:    
            if group in self.settings["linkprotect"]:
                if self.settings["linkprotect"][group] == 1:
                    if self.access(changer) > 5:
                        z = self.client.getGroup(group)
                        links = z.preventedJoinByTicket
                        if links == False:
                            z.preventedJoinByTicket = True
                            self.client.updateGroup(z)
                        if group in self.settings["protect"]:
                            if self.settings["protect"][group] == 2:
                                self.kicking(group, [changer])
                                self.banned(changer)

    def notif_accept_group_invite(self, op):
        group = op.param1
        joined = op.param2
        if op.param2 in self.stats['banned']['list']:
            self.kicking(op.param1, [op.param2])
        elif op.param2 in self.invites:
            self.kicking(op.param1, [op.param2])
            self.invites.remove(op.param2)
        elif self.settings["antibots"]:
            if self.access(joined) > 5:
                self.kicking(group, [joined])

    def notif_leave_group(self, op):
        if op.param1 in self.settings["strictmode"]:
            if op.param2 in self.stats["antijs"]["list"]:
                group = self.client.getGroup(op.param1)
                if group.invitee != None:
                    invtd = [o.mid for o in group.invitee]
                else:
                    invtd = [o.mid for o in group.members]
                if not set(self.stats["antijs"]["list"]).isdisjoint(invtd):
                    ajs = set(self.stats["antijs"]["list"]).intersection(invtd)
                    for inv in ajs:
                        self.inviting(op.param1, [inv])

    def accept_group_invite(self, op):
        if self.settings["autopurge"]:
            group = self.client.getGroup(op.param1)
            members = [o.mid for o in group.members]
            if not set(members).isdisjoint(self.stats["banned"]["list"]):
                band = set(members).intersection(self.stats["banned"]["list"])
                for ban in band:
                    self.kicking(op.param1, [ban])

    def notif_kick(self, op):
        self.count["countKick"] += 1

    def notif_invite(self, op):
        self.count["countInvite"] += 1

    def notif_cancel(self, op):
        self.count["countCancel"] += 1

    def receive_message(self, op):
        try:
            msg = op.message
            to = msg.to
            of = msg._from
            iz = msg.id
            text = msg.text
            if msg.contentType == 0:
                if None == msg.text:
                    return
                if text.lower().startswith(self.settings["rname"].lower() + " "):
                    rname = self.settings["rname"].lower() + " "
                else:
                    rname = self.settings["rname"].lower()
                if text.lower().startswith(self.settings["sname"].lower() + " "):
                    sname = self.settings["sname"].lower() + " "
                else:
                    sname = self.settings["sname"].lower()
                txt = msg.text.lower()
                txt = " ".join(txt.split())
                mykey = []
                if (txt.startswith(rname) or txt.startswith(sname)):
                    mykey = self.mycmd(txt, rname, sname)
                else:
                    mykey = []
                if txt == "ping": self.client.sendMessage(to, "PING!!!")
                if txt == "rname" and self.access(of) < 4:
                    self.client.sendMessage(to, self.settings['rname'].capitalize())
                if txt == "sname" and self.access(of) < 4:
                    self.client.sendMessage(to, self.settings['sname'].capitalize())
                if txt == "speed" and self.access(of) < 6:
                    run = time.time()
                    self.client.getProfile() 
                    start = time.time() - run
                    self.client.sendMessage(to, "Speed: %.4f ms" %(start))
                for a in mykey:
                    txt = a
                    if self.access(of) == 0:
                        if txt == "help":
                            if self.settings["rname"] == "": keyrname = ""
                            else: keyrname = self.settings["rname"].title() + " "
                            cmds = "HELLTERHEAD CORP."
                            cmds += "\n[ Single Protect v1.0 ]"
                            cmds += "\n\nSquad Name: " + self.settings['sname'].capitalize()
                            cmds += "\n────────────────────"
                            cmds += "\n\n❏ PROTECTION"
                            cmds += "\n    1. " + keyrname + "namelock /"
                            cmds += "\n    2. " + keyrname + "pictlock /"
                            cmds += "\n    3. " + keyrname + "linkprotect /"
                            cmds += "\n    4. " + keyrname + "denyinvite /"
                            cmds += "\n    5. " + keyrname + "protect /"
                            cmds += "\n    6. " + keyrname + "strictmode /"
                            cmds += "\n    7. " + keyrname + "allowban /"
                            cmds += "\n    8. " + keyrname + "autopurge /"
                            cmds += "\n    9. " + keyrname + "squadmode /"
                            cmds += "\n    10. " + keyrname + "antibots /"
                            cmds += "\n    11. " + keyrname + "protection max"
                            cmds += "\n    12. " + keyrname + "protection none"
                            cmds += "\n    13. " + keyrname + "prostatus"
                            cmds += "\n    14. " + keyrname + "cban"
                            cmds += "\n    15. " + keyrname + "bye"
                            cmds += "\n    16. " + keyrname + "groups"
                            cmds += "\n    17. " + keyrname + "protectlist"
                            cmds += "\n\n❏ UTILITY"
                            cmds += "\n    18. " + keyrname + "uprname *"
                            cmds += "\n    19. " + keyrname + "upsname *"
                            cmds += "\n    20. " + keyrname + "upname *"
                            cmds += "\n    21. " + keyrname + "upbio *"
                            cmds += "\n    22. " + keyrname + "uppict ^"
                            cmds += "\n    23. " + keyrname + "abort"
                            cmds += "\n    24. " + keyrname + "check"
                            cmds += "\n    25. " + keyrname + "status"
                            cmds += "\n    26. " + keyrname + "reboot"
                            cmds += "\n    27. " + keyrname + "kick ~"
                            cmds += "\n    28. " + keyrname + "invite ~"
                            cmds += "\n\n❏ PROMOTE/DEMOTE"
                            cmds += "\n    29. " + keyrname + "ban add ^"
                            cmds += "\n    30. " + keyrname + "ban del ^"
                            cmds += "\n    31. " + keyrname + "bot add ^"
                            cmds += "\n    32. " + keyrname + "bot del ^"
                            cmds += "\n    33. " + keyrname + "ajs add ^"
                            cmds += "\n    34. " + keyrname + "ajs del ^"
                            cmds += "\n    35. " + keyrname + "own add ^"
                            cmds += "\n    36. " + keyrname + "own del ^"
                            cmds += "\n    37. " + keyrname + "adm add ^"
                            cmds += "\n    38. " + keyrname + "adm del ^"
                            cmds += "\n    39. " + keyrname + "staff add ^"
                            cmds += "\n    40. " + keyrname + "staff del ^"
                            cmds += "\n\n❏ ACCESS"
                            cmds += "\n    41. " + keyrname + "banlist"
                            cmds += "\n    42. " + keyrname + "botlist"
                            cmds += "\n    43. " + keyrname + "ajslist"
                            cmds += "\n    44. " + keyrname + "ownlist"
                            cmds += "\n    45. " + keyrname + "admlist"
                            cmds += "\n    46. " + keyrname + "stafflist"
                            cmds += "\n\n────────────────────"
                            cmds += "\n[ ~ ] Reply"
                            cmds += "\n[ / ] Boolean"
                            cmds += "\n[ * ] Query"
                            cmds += "\n[ ^ ] Upload"
                            self.client.sendMessage(to, cmds)
                        elif txt == "check":
                            cstat = {"kick": "", "invite": ""}
                            try: self.client.inviteIntoGroup(to, [self.client.getProfile().mid]); cstat["invite"] = "⭕"
                            except: cstat["invite"] = "❌"
                            try: self.client.kickoutFromGroup(to, [self.client.getProfile().mid]); cstat["kick"] = "⭕"
                            except: cstat["kick"] = "❌"
                            msgs = "BOT CHECK\n"
                            msgs += "\n{}    Kick".format(cstat["kick"])
                            msgs += "\n{}    Invite".format(cstat["invite"])
                            msgs += "\n────────────────────"
                            msgs += "\nKick: {}".format(self.count["countKick"])
                            msgs += "\nInvite: {}".format(self.count["countInvite"])
                            msgs += "\nCancel: {}".format(self.count["countCancel"])
                            self.client.sendMessage(to, msgs)
                        elif txt == "groups":
                            if msg.toType == 2:
                                glist = self.client.getGroupIdsJoined()
                                glists = self.client.getGroups(glist)
                                no = 1
                                msgs = "GROUPLIST\n"
                                for ids in glists:
                                    msgs += "\n%i. %s" %(no, ids.name) + " (" + str(len(ids.members)) + ")"
                                    no = (no+1)
                                msgs += "\n\nTotal %i Groups" %len(glists)
                                self.client.sendMessage(to, "{}".format(str(msgs)))
                        elif txt == "status":
                            msgs = "BOT STATUS\n"
                            if self.settings["autopurge"] == True: msgs += "\n⚪    Auto Purge"
                            else: msgs += "\n⚫    Auto Purge"
                            if self.settings["allowban"] == True: msgs += "\n⚪    Allow Banned"
                            else: msgs += "\n⚫    Allow Banned"
                            if self.settings["sqmode"] == True: msgs += "\n⚪    Squad Mode"
                            else: msgs += "\n⚫    Squad Mode"
                            if self.settings["antibots"] == True: msgs += "\n⚪    Anti Bots"
                            else: msgs += "\n⚫    Anti Bots"
                            self.client.sendMessage(to, msgs)
                        elif txt == "prostatus":
                            group = self.client.getGroup(to)
                            msgs = "PROTECTION STATUS\n"
                            msgs += "\nGroup Name: {}".format(group.name)
                            msgs += "\nGroup ID: {}".format(group.id)
                            msgs += "\n────────────────────"
                            if to in self.settings["namelock"]: msgs += "\n⚪    Name Lock"
                            else: msgs += "\n⚫    Name Lock"
                            if to in self.settings["pictlock"]: msgs += "\n⚪    Picture Lock"
                            else: msgs += "\n⚫    Picture Lock"
                            if to in self.settings["linkprotect"]: msgs += "\n⚪    Link Protect"
                            else: msgs += "\n⚫    Link Protect"
                            if to in self.settings["denyinvite"]: msgs += "\n⚪    Deny Invite"
                            else: msgs += "\n⚫    Deny Invite"
                            if to in self.settings["protect"]: msgs += "\n⚪    Protect"
                            else: msgs += "\n⚫    Protect"
                            if to in self.settings["lockcancel"]: msgs += "\n⚪    Lock Cancel"
                            else: msgs += "\n⚫    Lock Cancel"
                            if to in self.settings["strictmode"]: msgs += "\n⚪    Strict Mode"
                            else: msgs += "\n⚫    Strict Mode"
                            self.client.sendMessage(to, msgs)
                        elif txt == "protectlist":
                            msgs = "PROTECT LIST\n"
                            protects = self.settings["protect"]
                            a = 1
                            ma = "\nProtect:"
                            for gids in protects:
                                ma += "\n  %i. %s" %(a, self.client.getGroup(gids).name)
                                a = (a+1)
                            msgs += ma + "\n"
                            namelocks = self.settings["namelock"]
                            b = 1
                            mb = "\nName Lock:"
                            for gids in namelocks:
                                mb += "\n  %i. %s" %(b, self.client.getGroup(gids).name)
                                b = (b+1)
                            msgs += mb + "\n"
                            pictlocks = self.settings["pictlock"]
                            c = 1
                            mc = "\nPicture Lock:"
                            for gids in pictlocks:
                                mc += "\n  %i. %s" %(c, self.client.getGroup(gids).name)
                                c = (c+1)
                            msgs += mc + "\n"
                            linkprotects = self.settings["linkprotect"]
                            d = 1
                            md = "\nLink Protect:"
                            for gids in linkprotects:
                                md += "\n  %i. %s" %(d, self.client.getGroup(gids).name)
                                d = (d+1)
                            msgs += md + "\n"
                            denyinvites = self.settings["denyinvite"]
                            e = 1
                            me = "\nDeny Invite:"
                            for gids in denyinvites:
                                me += "\n  %i. %s" %(e, self.client.getGroup(gids).name)
                                e = (e+1)
                            msgs += me + "\n"
                            lockcancels = self.settings["lockcancel"]
                            f = 1
                            mf = "\nLock Cancel:"
                            for gids in lockcancels:
                                mf += "\n  %i. %s" %(f, self.client.getGroup(gids).name)
                                f = (f+1)
                            msgs += mf + "\n"
                            strictmodes = self.settings["strictmode"]
                            g = 1
                            mg = "\nStrict Mode:"
                            for gids in strictmodes:
                                mg += "\n  %i. %s" %(g, self.client.getGroup(gids).name)
                                g = (g+1)
                            msgs += mg
                            self.client.sendMessage(to, "{}".format(str(msgs)))
                        elif txt == "abort":
                            self.stats["banned"]["add"] = False
                            self.stats["banned"]["del"] = False
                            self.stats["bots"]["add"] = False
                            self.stats["bots"]["del"] = False
                            self.stats["antijs"]["add"] = False
                            self.stats["antijs"]["del"] = False
                            self.stats["owners"]["add"] = False
                            self.stats["owners"]["del"] = False
                            self.stats["admins"]["add"] = False
                            self.stats["admins"]["del"] = False
                            self.stats["staffs"]["add"] = False
                            self.stats["staffs"]["del"] = False
                            self.settings["pictprofile"] = False
                            self.settings["pictprofile"] = False
                            self.client.sendMessage(to, "Command aborted.")
                        elif txt == "reboot":
                            self.client.sendMessage(to, "Restarting bot system...")
                            self.settings["restartpoint"] = to
                            time.sleep(1)
                            python3 = sys.executable
                            os.execl(python3, python3, *sys.argv)
                        elif txt == "bye":
                            self.client.leaveGroup(to)
                        elif txt == "cban":
                            amount = len(self.stats["banned"]["list"])
                            self.stats["banned"]["list"] = []
                            self.client.sendMessage(to, "Unbanned %s account." %amount)
                        elif txt == "kick":
                            if msg.relatedMessageId != None:
                                hlth = self.client.getRecentMessagesV2(to, 1001)
                                for i in hlth:
                                    if i.id in msg.relatedMessageId:
                                        self.client.kickoutFromGroup(to, [i._from])
                        elif txt == "invite":
                            if msg.relatedMessageId != None:
                                hlth = self.client.getRecentMessagesV2(to, 1001)
                                for i in hlth:
                                    if i.id in msg.relatedMessageId:
                                        self.client.findAndAddContactsByMid(i._from)
                                        self.client.inviteIntoGroup(to, [i._from])
                        elif txt.startswith("namelock "):
                            spl = txt.replace("namelock ", "")
                            if spl == "on":
                                if to in self.settings["namelock"]:
                                    self.client.sendMessage(to, "Namelock already enabled.")
                                else:
                                    self.settings["namelock"][to] = {"on": 1, "name": self.client.getGroup(to).name}
                                    self.client.sendMessage(to, "Namelock enabled.")
                            elif spl == "off":
                                if to in self.settings["namelock"]:
                                    del self.settings["namelock"][to]
                                    self.client.sendMessage(to, "Namelock disabled.")
                                else: self.client.sendMessage(to, "Namelock already disabled.")
                        elif txt.startswith("pictlock "):
                            spl = txt.replace("pictlock ", "")
                            if spl == "on":
                                if to in self.settings["pictlock"]:
                                    self.client.sendMessage(to, "Pictlock already enabled.")
                                else:
                                    self.settings["pictlock"][to] = {"on": 1, "pict": self.client.getGroup(to).pictureStatus}
                                    self.client.sendMessage(to, "Pictlock enabled.")
                            elif spl == "off":
                                if to in self.settings["pictlock"]:
                                    del self.settings["pictlock"][to]
                                    self.client.sendMessage(to, "Pictlock disabled.")
                                else: self.client.sendMessage(to, "Pictlock already disabled.")
                        elif txt.startswith("linkprotect "):
                            spl = txt.replace("linkprotect ", "")
                            if spl == "on":
                                if to in self.settings["linkprotect"]:
                                    self.client.sendMessage(to, "Linkprotection already enabled.")
                                else:
                                    self.settings["linkprotect"][to] = 1
                                    group = self.client.getGroup(to)
                                    links = group.preventedJoinByTicket
                                    if links == False:
                                        group.preventedJoinByTicket = True
                                        self.client.updateGroup(group)
                                    self.client.sendMessage(to, "Linkprotection enabled.")
                            elif spl == "off":
                                if to in self.settings["linkprotect"]:
                                    del self.settings["linkprotect"][to]
                                    self.client.sendMessage(to, "Linkprotection disabled.")
                                else: self.client.sendMessage(to, "Linkprotection already disabled.")
                        elif txt.startswith("strictmode "):
                            spl = txt.replace("strictmode ", "")
                            if spl == "on":
                                if to in self.settings["strictmode"]:
                                    self.client.sendMessage(to, "Strictmode already enabled.")
                                else:
                                    self.settings["strictmode"][to] = 1
                                    group = self.client.getGroup(to)
                                    if group.invitee != None:
                                        invtd = [o.mid for o in group.invitee]
                                    else:
                                        invtd = [o.mid for o in group.members]
                                    if not set(self.stats["antijs"]["list"]).isdisjoint(invtd):
                                        ajs = set(self.stats["antijs"]["list"]).intersection(invtd)
                                        for inv in ajs:
                                            self.client.inviteIntoGroup(to, [inv])
                                    self.client.sendMessage(to, "Strictmode enabled.")
                            elif spl == "off":
                                if to in self.settings["strictmode"]:
                                    del self.settings["strictmode"][to]
                                    group = self.client.getGroup(to)
                                    if group.preventedJoinByTicket == True:
                                        group.preventedJoinByTicket = False
                                        self.client.updateGroup(group)
                                        link = self.client.reissueGroupTicket(to)
                                        invtd = [o.mid for o in group.members]
                                        if not set(self.stats["antijs"]["list"]).isdisjoint(invtd):
                                            ajs = set(self.stats["antijs"]["list"]).intersection(invtd)
                                            for inv in ajs:
                                               self.client.sendMessage(inv, "line.me/R/ti/g/" + link)
                                    self.client.sendMessage(to, "Strictmode disabled.")
                                else: self.client.sendMessage(to, "Strictmode already disabled.")
                        elif txt.startswith("denyinvite "):
                            spl = txt.replace("denyinvite ", "")
                            if spl == "max":
                                if to in self.settings["denyinvite"]:
                                    if self.settings["denyinvite"][to] == 2:
                                        self.client.sendMessage(to, "Denyinvite Max already enabled")
                                    else:
                                        self.settings["denyinvite"][to] = 2
                                        self.client.sendMessage(to, "Denyinvite Max enabled.")
                                else:
                                    self.settings["denyinvite"][to] = 2
                                    self.client.sendMessage(to, "Denyinvite Max enabled.")
                            elif spl == "on":
                                if to in self.settings["denyinvite"]:
                                    if self.settings["denyinvite"][to] == 1:
                                        self.client.sendMessage(to,"Denyinvite already enabled")
                                    else:
                                        self.settings["denyinvite"][to] = 1
                                        self.client.sendMessage(to, "Denyinvite enabled.")
                                else:
                                    self.settings["denyinvite"][to] = 1
                                    self.client.sendMessage(to, "Denyinvite enabled.")
                            elif spl == "off":
                                if to in self.settings["denyinvite"]:
                                    del self.settings["denyinvite"][to]
                                    self.client.sendMessage(to, "Denyinvite disabled.")
                                else:
                                    self.client.sendMessage(to, "Denyinvite already disabled.")
                        elif txt.startswith("protect "):
                            spl = txt.replace("protect ", "")
                            if spl == "max":
                                if to in self.settings["protect"]:
                                    if self.settings["protect"][to] == 2:
                                        self.client.sendMessage(to, "Protect Max already enabled")
                                    else:
                                        self.settings["protect"][to] = 2
                                        self.client.sendMessage(to, "Protect Max enabled.")
                                else:
                                    self.settings["protect"][to] = 2
                                    self.client.sendMessage(to, "Protect Max enabled.")
                            elif spl == "on":
                                if to in self.settings["protect"]:
                                    if self.settings["protect"][to] == 1:
                                        self.client.sendMessage(to, "Protect already enabled")
                                    else:
                                        self.settings["protect"][to] = 1
                                        self.client.sendMessage(to, "Protect enabled.")
                                else:
                                    self.settings["protect"][to] = 1
                                    self.client.sendMessage(to, "Protect enabled.")
                            elif spl == "off":
                                if to in self.settings["protect"]:
                                    del self.settings["protect"][to]
                                    self.client.sendMessage(to, "Protect disabled.")
                                else:
                                    self.client.sendMessage(to, "Protect already disabled.")
                        elif txt.startswith("lockcancel "):
                            spl = txt.replace("lockcancel ", "")
                            if spl == "on":
                                if to in self.settings["lockcancel"]:
                                    if self.settings["lockcancel"][to] == 1:
                                        self.client.sendMessage(to, "Lockcancel already enabled.")
                                    else:
                                        self.settings["lockcancel"][to] = 1
                                        self.client.sendMessage(to, "Lockcancel enabled.")
                            elif spl == "off":
                                if self.settings["lockcancel"]:
                                    del self.settings["lockcancel"][to]
                                    self.client.sendMessage(to, "Lockcancel disabled.")
                                else:
                                    self.client.sendMessage(to, "Lockcancel already disabled.")
                        elif txt.startswith("allowban "):
                            spl = txt.replace("allowban ", "")
                            if spl == "on":
                                if self.settings['allowban']:
                                    self.client.sendMessage(to, "Allowban already enabled.")
                                else:
                                    self.settings["allowban"] = True
                                    self.client.sendMessage(to, "Allowban enabled.")
                            elif spl == "off":
                                if self.settings['allowban']:
                                    self.settings["allowban"] = False
                                    self.client.sendMessage(to, "Allowban disabled.")
                                else:
                                    self.client.sendMessage(to, "Allowban already disabled.")
                        elif txt.startswith("autopurge "):
                            spl = txt.replace("autopurge ", "")
                            if spl == "on":
                                if self.settings['autopurge']:
                                    self.client.sendMessage(to, "Autopurge already enabled.")
                                else:
                                    self.settings["autopurge"] = True
                                    self.client.sendMessage(to, "Autopurge enabled.")
                            elif spl == "off":
                                if self.settings['autopurge']:
                                    self.settings["autopurge"] = False
                                    self.client.sendMessage(to, "Autopurge disabled.")
                                else:
                                    self.client.sendMessage(to, "Autopurge already disabled.")
                        elif txt.startswith("squadmode "):
                            spl = txt.replace("squadmode ", "")
                            if spl == "on":
                                if self.settings['sqmode']:
                                    self.client.sendMessage(to, "Squadmode already enabled.")
                                else:
                                    self.settings["sqmode"] = True
                                    self.client.sendMessage(to, "Squadmode enabled.")
                            elif spl == "off":
                                if self.settings['sqmode']:
                                    self.settings["sqmode"] = False
                                    self.client.sendMessage(to, "Squadmode disabled.")
                                else:
                                    self.client.sendMessage(to, "Squadmode already disabled.")
                        elif txt.startswith("antibots "):
                            spl = txt.replace("antibots ", "")
                            if spl == "on":
                                if self.settings['antibots']:
                                    self.client.sendMessage(to, "Antibots already enabled.")
                                else:
                                    self.settings["antibots"] = True
                                    self.client.sendMessage(to, "Antibots enabled.")
                            elif spl == "off":
                                if self.settings['antibots']:
                                    self.settings["antibots"] = False
                                    self.client.sendMessage(to, "Antibots disabled.")
                                else:
                                    self.client.sendMessage(to, "Antibots already disabled.")
                        elif txt == "protection max":
                            self.settings["protect"][to] = 2
                            self.settings["denyinvite"][to] = 2
                            self.settings["lockcancel"][to] = 1
                            self.settings["linkprotect"][to] = 1
                            group = self.client.getGroup(to)
                            self.settings["namelock"][to] = {"on": 1, "name": group.name}
                            self.settings["pictlock"][to] = {"on": 1, "pict": group.pictureStatus}
                            links = group.preventedJoinByTicket
                            if links == False:
                                group.preventedJoinByTicket = True
                                self.client.updateGroup(group)
                            self.client.sendMessage(to, "Max protection enabled.")
                        elif txt == "protection none":
                            if to in self.settings["protect"]: del self.settings["protect"][to]
                            if to in self.settings["denyinvite"]: del self.settings["denyinvite"][to]
                            if to in self.settings["lockcancel"]: del self.settings["lockcancel"][to]
                            if to in self.settings["linkprotect"]: del self.settings["linkprotect"][to]
                            if to in self.settings["namelock"]: del self.settings["namelock"][to]
                            if to in self.settings["pictlock"]: del self.settings["pictlock"][to]
                            self.client.sendMessage(to, "All protection disabled.")
                        elif txt.startswith("ban "):
                            spl = txt.replace("ban ", "")
                            if spl == "add":
                                self.stats["banned"]["add"] = True
                                self.client.sendMessage(to, "Send contact...")
                            elif spl == "del":
                                self.stats["banned"]["del"] = True
                                self.client.sendMessage(to, "Send contact...")
                        elif txt.startswith("bot "):
                            spl = txt.replace("bot ", "")
                            if spl == "add":
                                self.stats["bots"]["add"] = True
                                self.client.sendMessage(to, "Send contact...")
                            elif spl == "del":
                                self.stats["bots"]["del"] = True
                                self.client.sendMessage(to, "Send contact...")
                        elif txt.startswith("ajs "):
                            spl = txt.replace("ajs ", "")
                            if spl == "add":
                                self.stats["antijs"]["add"] = True
                                self.client.sendMessage(to, "Send contact...")
                            elif spl == "del":
                                self.stats["antijs"]["del"] = True
                                self.client.sendMessage(to, "Send contact...")
                        elif txt.startswith("own "):
                            spl = txt.replace("own ", "")
                            if spl == "add":
                                self.stats["owners"]["add"] = True
                                self.client.sendMessage(to, "Send contact...")
                            elif spl == "del":
                                self.stats["owners"]["del"] = True
                                self.client.sendMessage(to, "Send contact...")
                        elif txt.startswith("adm "):
                            spl = txt.replace("adm ", "")
                            if spl == "add":
                                self.stats["admins"]["add"] = True
                                self.client.sendMessage(to, "Send contact...")
                            elif spl == "del":
                                self.stats["admins"]["del"] = True
                                self.client.sendMessage(to, "Send contact...")
                        elif txt.startswith("staff "):
                            spl = txt.replace("staff ", "")
                            if spl == "add":
                                self.stats["staffs"]["add"] = True
                                self.client.sendMessage(to, "Send contact...")
                            elif spl == "del":
                                self.stats["staffs"]["del"] = True
                                self.client.sendMessage(to, "Send contact...")
                        elif txt == "banlist":
                            if msg.toType == 2:
                                user = self.stats["banned"]["list"]
                                no = 1
                                msgs = "BANNED LIST\n"
                                for ids in user:
                                    users = self.client.getContact(ids)
                                    msgs += "\n%i. %s" %(no, users.displayName)
                                    no = (no+1)
                                msgs += "\n\nTotal %i Banned" %len(user)
                                self.client.sendMessage(to, "{}".format(str(msgs)))
                        elif txt == "botlist":
                            if msg.toType == 2:
                                user = self.stats["bots"]["list"]
                                no = 1
                                msgs = "BOT LIST\n"
                                for ids in user:
                                    users = self.client.getContact(ids)
                                    msgs += "\n%i. %s" %(no, users.displayName)
                                    no = (no+1)
                                msgs += "\n\nTotal %i Bots" %len(user)
                                self.client.sendMessage(to, "{}".format(str(msgs)))
                        elif txt == "ajslist":
                            if msg.toType == 2:
                                user = self.stats["antijs"]["list"]
                                no = 1
                                msgs = "ANTI JS LIST\n"
                                for ids in user:
                                    users = self.client.getContact(ids)
                                    msgs += "\n%i. %s" %(no, users.displayName)
                                    no = (no+1)
                                msgs += "\n\nTotal %i Antijs" %len(user)
                                self.client.sendMessage(to, "{}".format(str(msgs)))
                        elif txt == "ownlist":
                            if msg.toType == 2:
                                user = self.stats["owners"]["list"]
                                no = 1
                                msgs = "OWNER LIST\n"
                                for ids in user:
                                    users = self.client.getContact(ids)
                                    msgs += "\n%i. %s" %(no, users.displayName)
                                    no = (no+1)
                                msgs += "\n\nTotal %i Owners" %len(user)
                                self.client.sendMessage(to, "{}".format(str(msgs)))
                        elif txt == "admlist":
                            if msg.toType == 2:
                                user = self.stats["admins"]["list"]
                                no = 1
                                msgs = "ADMIN LIST\n"
                                for ids in user:
                                    users = self.client.getContact(ids)
                                    msgs += "\n%i. %s" %(no, users.displayName)
                                    no = (no+1)
                                msgs += "\n\nTotal %i Admins" %len(user)
                                self.client.sendMessage(to, "{}".format(str(msgs)))
                        elif txt == "stafflist":
                            if msg.toType == 2:
                                user = self.stats["staffs"]["list"]
                                no = 1
                                msgs = "STAFF LIST\n"
                                for ids in user:
                                    users = self.client.getContact(ids)
                                    msgs += "\n%i. %s" %(no, users.displayName)
                                    no = (no+1)
                                msgs += "\n\nTotal %i Staffs" %len(user)
                                self.client.sendMessage(to, "{}".format(str(msgs)))
                        elif txt.startswith("uprname "):
                            string = txt.split(" ")[1]
                            self.settings['rname'] = string
                            self.client.sendMessage(to, "Responsename update to {}".format(self.settings['rname']))
                        elif txt.startswith("upsname "):
                            string = txt.split(" ")[1]
                            self.settings['sname'] = string
                            self.client.sendMessage(to, "Squadname update to {}".format(self.settings['sname']))
                        elif txt.startswith("upbio "):
                            string = txt.split("upbio ")[1]
                            if len(string) <= 500:
                                bio = self.client.getProfile()
                                bio.statusMessage = string
                                self.client.updateProfile(bio)
                                self.client.sendMessage(to, "Bio updated to {}".format(string))
                            else: self.client.sendMessage(to, "Text is limit.")
                        elif txt.startswith("upname "):
                            string = txt.split("upname ")[1]
                            if len(string) <= 20:
                                name = self.client.getProfile()
                                name.displayName = string.title()
                                self.client.updateProfile(name)
                                self.client.sendMessage(to, "Name updated to {}".format(string.title()))
                            else: self.client.sendMessage(to, "Text is limit.")
                        elif txt == "uppict":
                            self.settings["pictprofile"] = True
                            self.client.sendMessage(to, "Send picture...")
            if msg.contentType == 1:
                if self.access(of) == 0:
                    if self.settings["pictprofile"] == True:
                        path = self.client.downloadObjectMsg(iz)
                        self.client.updateProfilePicture(path)
                        self.settings["pictprofile"] = False
                        self.client.sendMessage(to, "Picture profile updated.")
            if msg.contentType == 13:
                if self.access(of) == 0:
                    if self.stats["banned"]["add"] == True:
                        if msg.contentMetadata["mid"] not in self.client.profile.mid:
                            if msg.contentMetadata["mid"] in self.stats["banned"]["list"]:
                                self.client.sendMessage(to, "{} already in blacklist.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                self.stats["banned"]["add"] = False
                            else:
                                if msg.contentMetadata["mid"] not in (self.stats["owners"]["list"], self.stats["admins"]["list"], self.stats["staffs"]["list"], self.stats["bots"]["list"], self.stats["antijs"]["list"]):
                                    self.stats["banned"]["list"].append(msg.contentMetadata["mid"])
                                    self.client.sendMessage(to, "{} added in blacklist.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                    self.stats["banned"]["add"] = False
                                else: self.client.sendMessage(to, "User in whitelist.")
                                self.stats["banned"]["add"] = False
                    elif self.stats["banned"]["del"] == True:
                        if msg.contentMetadata["mid"] not in self.client.profile.mid:
                            if msg.contentMetadata["mid"] in self.stats["banned"]["list"]:
                                self.stats["banned"]["list"].remove(msg.contentMetadata["mid"])
                                self.client.sendMessage(to, "{} removed from blacklist.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                self.stats["banned"]["del"] = False
                            else: self.client.sendMessage(to, "User not in blacklist.")
                            self.stats["banned"]["del"] = False
                    elif self.stats["bots"]["add"] == True:
                        if msg.contentMetadata["mid"] not in self.client.profile.mid:
                            if msg.contentMetadata["mid"] in self.stats["bots"]["list"]:
                                self.client.sendMessage(to, "{} already in bots.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                self.stats["bots"]["add"] = False
                            else:
                                if msg.contentMetadata["mid"] not in self.stats["banned"]["list"]:
                                    self.stats["bots"]["list"].append(msg.contentMetadata["mid"])
                                    self.client.sendMessage(to, "{} added in bots.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                    self.stats["bots"]["add"] = False
                                else: self.client.sendMessage(to, "User in blacklist.")
                                self.stats["bots"]["add"] = False
                    elif self.stats["bots"]["del"] == True:
                        if msg.contentMetadata["mid"] not in self.client.profile.mid:
                            if msg.contentMetadata["mid"] in self.stats["bots"]["list"]:
                                self.stats["bots"]["list"].remove(msg.contentMetadata["mid"])
                                self.client.sendMessage(to, "{} removed from bots.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                self.stats["bots"]["del"] = False
                            else: self.client.sendMessage(to, "User not in bots.")
                            self.stats["bots"]["del"] = False
                    elif self.stats["antijs"]["add"] == True:
                        if msg.contentMetadata["mid"] not in self.client.profile.mid:
                            if msg.contentMetadata["mid"] in self.stats["antijs"]["list"]:
                                self.client.sendMessage(to, "{} already in antijs.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                self.stats["antijs"]["add"] = False
                            else:
                                if msg.contentMetadata["mid"] not in self.stats["banned"]["list"]:
                                    self.stats["antijs"]["list"].append(msg.contentMetadata["mid"])
                                    self.client.sendMessage(to, "{} added in antijs.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                    self.stats["antijs"]["add"] = False
                                else: self.client.sendMessage(to, "User in blacklist.")
                                self.stats["antijs"]["add"] = False
                    elif self.stats["antijs"]["del"] == True:
                        if msg.contentMetadata["mid"] not in self.client.profile.mid:
                            if msg.contentMetadata["mid"] in self.stats["antijs"]["list"]:
                                self.stats["antijs"]["list"].remove(msg.contentMetadata["mid"])
                                self.client.sendMessage(to, "{} removed from antijs.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                self.stats["antijs"]["del"] = False
                            else: self.client.sendMessage(to, "User not in antijs.")
                            self.stats["antijs"]["del"] = False
                    elif self.stats["owners"]["add"] == True:
                        if msg.contentMetadata["mid"] not in self.client.profile.mid:
                            if msg.contentMetadata["mid"] in self.stats["owners"]["list"]:
                                self.client.sendMessage(to, "{} already in owners.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                self.stats["owners"]["add"] = False
                            else:
                                if msg.contentMetadata["mid"] not in self.stats["banned"]["list"]:
                                    self.stats["owners"]["list"].append(msg.contentMetadata["mid"])
                                    self.client.sendMessage(to, "{} added in owners.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                    self.stats["owners"]["add"] = False
                                else: self.client.sendMessage(to, "User in blacklist.")
                                self.stats["owners"]["add"] = False
                    elif self.stats["owners"]["del"] == True:
                        if msg.contentMetadata["mid"] not in self.client.profile.mid:
                            if msg.contentMetadata["mid"] in self.stats["owners"]["list"]:
                                self.stats["owners"]["list"].remove(msg.contentMetadata["mid"])
                                self.client.sendMessage(to, "{} removed from owners.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                self.stats["owners"]["del"] = False
                            else: self.client.sendMessage(to, "User not in owners.")
                            self.stats["owners"]["del"] = False
                    elif self.stats["admins"]["add"] == True:
                        if msg.contentMetadata["mid"] not in self.client.profile.mid:
                            if msg.contentMetadata["mid"] in self.stats["admins"]["list"]:
                                self.client.sendMessage(to, "{} already in admins.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                self.stats["admins"]["add"] = False
                            else:
                                if msg.contentMetadata["mid"] not in self.stats["banned"]["list"]:
                                    self.stats["admins"]["list"].append(msg.contentMetadata["mid"])
                                    self.client.sendMessage(to, "{} added in admins.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                    self.stats["admins"]["add"] = False
                                else: self.client.sendMessage(to, "User in blacklist.")
                                self.stats["admins"]["add"] = False
                    elif self.stats["admins"]["del"] == True:
                        if msg.contentMetadata["mid"] not in self.client.profile.mid:
                            if msg.contentMetadata["mid"] in self.stats["admins"]["list"]:
                                self.stats["admins"]["list"].remove(msg.contentMetadata["mid"])
                                self.client.sendMessage(to, "{} removed from admins.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                self.stats["admins"]["del"] = False
                            else: self.client.sendMessage(to, "User not in admins.")
                            self.stats["admins"]["del"] = False
                    elif self.stats["staffs"]["add"] == True:
                        if msg.contentMetadata["mid"] not in self.client.profile.mid:
                            if msg.contentMetadata["mid"] in self.stats["staffs"]["list"]:
                                self.client.sendMessage(to, "{} already in staffs.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                self.stats["staffs"]["add"] = False
                            else:
                                if msg.contentMetadata["mid"] not in self.stats["banned"]["list"]:
                                    self.stats["staffs"]["list"].append(msg.contentMetadata["mid"])
                                    self.client.sendMessage(to, "{} added in staffs.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                    self.stats["staffs"]["add"] = False
                                else: self.client.sendMessage(to, "User in blacklist.")
                                self.stats["staffs"]["add"] = False
                    elif self.stats["staffs"]["del"] == True:
                        if msg.contentMetadata["mid"] not in self.client.profile.mid:
                            if msg.contentMetadata["mid"] in self.stats["staffs"]["list"]:
                                self.stats["staffs"]["list"].remove(msg.contentMetadata["mid"])
                                self.client.sendMessage(to, "{} removed from staffs.".format(self.client.getContact(msg.contentMetadata["mid"]).displayName))
                                self.stats["staffs"]["del"] = False
                            else: self.client.sendMessage(to, "User not in staffs.")
                            self.stats["staffs"]["del"] = False
        except Exception as e:
            e = traceback.format_exc()
            if "EOFError" in e: pass
            elif "ShouldSyncException" in e or "LOG_OUT" in e:
                python3 = sys.executable
                os.execl(python3, python3, *sys.argv)
            else: traceback.print_exc()
