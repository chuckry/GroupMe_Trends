import sys
import operator
import time
import requests
import pprint
import json

GM_URL = "https://api.groupme.com/v3"
TOKEN = "1ba57e60aeb60134ef3103715af1578e"
SECS_PER_SIX_MONTHS = 15552000

if len(sys.argv) < 2:
	print "Need to specify group name in command line!"
	sys.exit(1)

groupName = sys.argv[1]

def makeGetRequest(url, params):
	resp = requests.get(url=url, params=params)
	try:
		data = json.loads(resp.content)
		return data
	except ValueError:
		return

def checkErrorCode(data):
	try:
		if data['meta']['code'] >= 400:
			print "Failed with error code " + str(data['meta']['code']) + '.'
			sys.exit(1)
	except:
		return

class GroupMe:
	def __init__(self):
		# Store user info
		self.mUserInfo = makeGetRequest(GM_URL + "/users/me", {'token': TOKEN})
		self.mNamesToIds = {}
		self.mGroups = {}
		self.mMessages = []

	def getGroups(self):
		# Store user's groups
		data = makeGetRequest(GM_URL + "/groups", {'token': TOKEN, 'per_page': 100})
		checkErrorCode(data)

		for group in data['response']:
			self.mGroups[group['name']] = group

		# Store groups names and IDs
		for name, groupInfo in self.mGroups.iteritems():
			self.mNamesToIds[name] = groupInfo['id']

	# Trim untouched groups
	def getGroupsToDelete(self):
		if not self.mGroups:
			self.getGroups()

		groupsToRecency = {}
		for name, groupInfo in self.mGroups.iteritems():
			groupsToRecency[name] = groupInfo['messages']['last_message_created_at']

		relevantGroups = [x for x in groupsToRecency if groupsToRecency[x] >= time.time() - SECS_PER_SIX_MONTHS]
		choppingBlockGroups = list(set(groupsToRecency.keys()) - set(relevantGroups))
		return choppingBlockGroups

	def getMessages(self, groupName, before_id):
		if not self.mNamesToIds:
			self.getGroups()
		groupId = self.mNamesToIds[groupName]

		if before_id == None:
			before_id = self.mGroups[groupName]['messages']['last_message_id']

		data = makeGetRequest(
			GM_URL + "/groups/" + str(groupId) + "/messages",
			{'token': TOKEN, 'before_id': before_id, 'limit': 100}
		)
		checkErrorCode(data)
		return data

	# Return member with highest likes:messages
	#	- number of messages must exceed threshold
	#	- threshold based on (total group messages) / (total group members)
	def mostPopularMember(self, groupName):
		self.mMessages = []
		msg_id = None
		data = self.getMessages(groupName, msg_id)
		while data:
			self.mMessages.extend(data['response']['messages'])
			msg_id = self.mMessages[-1]['id']
			data = self.getMessages(groupName, msg_id)

		membersToLikes = {}
		membersToMsgs = {}
		for msg in self.mMessages:
			# TODO: "GroupMe" messages should translate to a user
			if msg['name'] == "GroupMe":
				continue

			if msg['name'] not in membersToLikes:
				membersToLikes[msg['name']] = 0
			membersToLikes[msg['name']] += len(msg['favorited_by'])

			if msg['name'] not in membersToMsgs:
				membersToMsgs[msg['name']] = 0
			membersToMsgs[msg['name']] += 1

		memberRatios = {}
		for member in membersToLikes:
			memberRatios[member] = membersToLikes[member] / float(membersToMsgs[member])
		return sorted(memberRatios.items(), key=operator.itemgetter(1), reverse=True)


g = GroupMe()
# pprint.pprint(g.getGroupsToDelete())
print "***** GROUPME POPULARITY SCORES FOR " + groupName + " *****"
pprint.pprint(g.mostPopularMember(groupName))
print "***** (Number of Earned Likes) / (Total Number of Messages) per member. *****"








