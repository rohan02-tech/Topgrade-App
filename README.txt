TOP GRADE APP - LOCAL SETUP AND DEPLOYMENT GUIDE
====================================================

FOLDER STRUCTURE
-----------------
topgrade-app/
  backend/
    app.py                  Flask server, 4 API endpoints
    requirements.txt        Python dependencies
    database/
      schema.sql             table definitions
      seed.py                 builds and fills topgrade.db with real course data
      topgrade.db             SQLite database (already built)
    media/
      python-course/videos/   put lecture1.mp4 and lecture2.mp4 here
      java-course/videos/     put lecture1.mp4 and lecture2.mp4 here
  frontend/
    index.html               the app shell (home, header, nav, login)
    app.js                    all frontend logic, calls the backend API


RUNNING IT LOCALLY
-----------------
1. Install Python 3 if you don't have it already.

2. Open a terminal in the backend folder and install dependencies:
     cd topgrade-app/backend
     pip install -r requirements.txt

3. (Only needed once, already done for you, but if you ever want to reset the data):
     python database/seed.py

4. Start the backend server:
     python app.py
   This runs on http://127.0.0.1:5000

5. Open frontend/index.html directly in your browser (just double-click it, or
   right click and Open With Browser). It will call the backend automatically.

   Login with the name "Rohan" or "Aman" to test both experiences.


ADDING YOUR VIDEO FILES
-----------------
Drop your real .mp4 files into:
  backend/media/python-course/videos/lecture1.mp4
  backend/media/python-course/videos/lecture2.mp4
  backend/media/java-course/videos/lecture1.mp4
  backend/media/java-course/videos/lecture2.mp4

The filenames must match exactly, the database already points to these paths.


DEPLOYING TO PRODUCTION
-----------------
This app has two separate pieces that get deployed differently: the Flask
backend (API plus database) and the static frontend (HTML plus JavaScript).

BACKEND (Flask API):
  - Do not use "python app.py" in production, that is a development server only.
  - Use a proper WSGI server such as Gunicorn behind the scenes:
      pip install gunicorn
      gunicorn -w 4 -b 0.0.0.0:5000 app:app
  - Host it on a platform such as Render, Railway, or a small cloud VM
    (AWS EC2, DigitalOcean droplet, etc). All of these can run a Flask app
    with very little configuration.
  - For real usage with more than a couple of students, swap SQLite for a
    hosted database such as PostgreSQL, since SQLite is a single file and
    does not handle many simultaneous users well. The table structure in
    schema.sql can be translated to PostgreSQL with only minor changes.
  - Store your video files in cloud storage instead of the local media
    folder, for example Amazon S3 or Cloudflare R2, and update the
    video_path values in the database to point to those URLs.
  - Set proper CORS rules in app.py to only allow your real frontend domain,
    rather than allowing all origins.

FRONTEND (HTML plus JavaScript):
  - This is a static site, so it can be deployed to Netlify, Vercel, GitHub
    Pages, or Cloudflare Pages, all of which have free tiers.
  - Before deploying, update the API_BASE constant at the top of app.js from
    http://127.0.0.1:5000 to your real backend's public URL, for example
    https://api.topgradeinnovation.com

DOMAIN AND HTTPS:
  - Once both pieces are deployed, point your domain, www.topgradeinnovation.com,
    at the frontend, and something like api.topgradeinnovation.com at the backend.
  - Most hosting platforms mentioned above provide free HTTPS certificates
    automatically.

AUTHENTICATION NOTE:
  - The current login is a simple demo, matching typed names to two seeded
    students. Before real production use, this should be replaced with
    proper authentication, for example email and password with hashed
    passwords, or a login provider such as Google sign-in.
