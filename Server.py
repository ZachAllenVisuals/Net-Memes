from flask import Flask, render_template, request, make_response, redirect
from datetime import datetime, timedelta
import os
import random


app = Flask(__name__)


images_path = "/mnt/Ext_SSD/Net_Memes/static/images"


game_state = -1

# -1: Waiting for players
#  0: Waiting for Judge Submission
#  1: Waiting for Player Submission
#  2: Waiting for Judge Selection
#  Then go to 0 and start over

scoreboard = {"[Placeholder]":0};

active_players = [];

Judge = None;

most_recent_state_change = datetime.now() # datetime of most recent time the game_state changed

record = [];


class Single_Round(object):
	"""docstring for Single_Round"""
	def __init__(self, Judge = None):
		super(Single_Round, self).__init__()
		self.Judge = Judge
		self.Image_Path = None
		self.Suggestions_dict = {}
		self.Winner = None



message_dict = {"-1": "Waiting for more players...; Current Judge is %s", "0": "Waiting for Judge Submission; Current Judge is %s", "1": "Waiting for Player Submission; Current Judge is %s", "2": "Waiting for Judge Selection; Current Judge is %s"}

@app.route("/")
def main_switchbox():

	global game_state
	global current_round
	global most_recent_state_change

	username = request.cookies.get('username')
	
	if username is None:
		return render_template("New_User.html")

	if username not in active_players:
		active_players.append(username)

	print "[LOG] Access from %s"%(username)

	if len(active_players) < 3:
		print "[LOG] Too Few Players"
		game_state = -1
		most_recent_state_change = datetime.now() # datetime of most recent time the game_state changed

		return render_template("Waiting.html", status_message = message_dict[str(game_state)]%str(current_round.Judge))

	if current_round.Judge is None:
		current_round.Judge = random.choice(active_players)
		game_state = 0;

	if len(current_round.Suggestions_dict.items()) == len(active_players) - 1:
		game_state = 2
		most_recent_state_change = datetime.now() # datetime of most recent time the game_state changed


	if datetime.now() - most_recent_state_change > timedelta(minutes = 3) and game_state == 1: # Submission Timing
		game_state = 2;
		most_recent_state_change = datetime.now() # datetime of most recent time the game_state changed


	if datetime.now() - most_recent_state_change > timedelta(minutes = 2) and game_state != 1: # Judging Timing
		game_state = 0;
		current_round = Single_Round()
		print "[LOG] Game Forced Reset- delay of game on the Judge"
		most_recent_state_change = datetime.now() # datetime of most recent time the game_state changed



	if username == current_round.Judge:
		print "[LOG] Access from Judge"
		if game_state == 0:
			return render_template("Judge_Submission.html")
		elif game_state == 2:
			pass;
			return render_template("Judge_Selection.html", image_path = current_round.Image_Path, submissions = [(k, v) for k, v in current_round.Suggestions_dict.items()])
		else:
			return render_template("Waiting.html", status_message = message_dict[str(game_state)]%str(current_round.Judge))

	else:
		if game_state == 1 and (username not in current_round.Suggestions_dict):
			return render_template("Player_Submission.html", image_path = current_round.Image_Path)
		elif game_state == 2:
			return render_template("Judge_Selection.html", image_path = current_round.Image_Path, submissions = [(k, v) for k, v in current_round.Suggestions_dict.items()])
		else:
			return render_template("Waiting.html", status_message = message_dict[str(game_state)]%str(current_round.Judge))




@app.route("/new_user", methods=['POST'])
def new_user():

	global game_state
	global current_round
	global most_recent_state_change

	username = request.cookies.get('username')
	if username is not None:
		return main_switchbox()

	requested_username = request.form.get('username').encode('ascii', 'ignore')

	if (requested_username is None) or (requested_username in active_players):
		return render_template("New_User.html")

	active_players.append(requested_username)

	if len(active_players) == 3:
		game_state = 0;
		most_recent_state_change = datetime.now() # datetime of most recent time the game_state changed

		current_round.Judge = requested_username

	resp = make_response(render_template("Scoreboard.html"))
	resp.set_cookie('username', requested_username)

	return resp 



@app.route("/judge_submission", methods = ['POST'])
def judge_submission():

	global game_state
	global current_round
	global most_recent_state_change



	if request.cookies.get('username') != current_round.Judge:
		return redirect("/")

	print "[LOG] Judge submission"

	if 'Judge_Image' not in request.files:
		print "[LOG] File Not Present"
		return "SAD"

	submitted_image = request.files['Judge_Image']

	print "[LOG] Image: ", submitted_image

	if submitted_image.filename != "":
		print "[LOG] Image Exists"
		pre_split_extension = submitted_image.filename.split(".")[-1]
		if pre_split_extension in ["png", "jpg", "jpeg"]:
			random_id = str(random.randint(0, 10000)) + "." + pre_split_extension
		else:
			random_id = str(random.randint(0, 10000)) + ".png"

		current_round.Image_Path = os.path.join("/static/images", random_id)



		submitted_image.save(os.path.join(images_path, random_id))
		print "[LOG] Image Saved"

		game_state = 1
		most_recent_state_change = datetime.now()
	return redirect("/")


@app.route("/player_submission", methods = ['POST'])
def player_submission():

	global current_round
	global most_recent_state_change

	username = request.cookies.get('username')

	if username != current_round.Judge:
		suggestion = request.form.get('Submission', "")
		if suggestion != "":
			current_round.Suggestions_dict[username] = suggestion
			most_recent_state_change = datetime.now()
	return redirect("/")


@app.route("/judge_selection", methods=['POST'])
def judge_selection():
	global most_recent_state_change
	global current_round
	global game_state
	global active_players
	global record
	global scoreboard

	username = request.cookies.get('username')

	if username == current_round.Judge:
		selected_player = request.form.get('Selection', "")
		if selected_player != "" and selected_player in active_players:
			current_round.Winner = selected_player

			scoreboard[current_round.Winner] = scoreboard.setdefault(current_round.Winner, 0) + 1

			game_state = 0
			most_recent_state_change = datetime.now() # datetime of most recent time the game_state changed

			next_judge = random.choice(current_round.Suggestions_dict.keys())
			active_players = current_round.Suggestions_dict.keys() + [current_round.Judge]

			record.append(current_round)
			current_round = Single_Round()
			current_round.Judge = next_judge

	return redirect("/")



@app.route("/Scoreboard")
def get_scoreboard():
	username = request.cookies.get('username')

	return render_template("Scoreboard.html", username = username, user_scores = [(k,v) for k, v in scoreboard.items()], rounds = record)
	



if __name__ == "__main__":


	current_round = Single_Round()

	app.run(host='0.0.0.0', port = "80")
