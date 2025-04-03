from flask import Flask, redirect, url_for, render_template

app = Flask(__name__)

@app.route("/")
def index():
    username = "John" 
    intro = """Hi there! I'm John, and this is my personal Q&A site. I've created this space to interact with friends, colleagues, and anyone interested in connecting.

Feel free to ask me anything you're curious about - whether it's about my work, hobbies, opinions, or just something you'd like my perspective on. I'll do my best to answer your questions!
"""

    page = render_template(
        'index.html', 
        user=username, 
        introduction=intro
        )

    return page




if __name__ == "__main__":
    app.run(debug=True)