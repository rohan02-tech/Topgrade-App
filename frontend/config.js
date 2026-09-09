/*
  config.js
  The ONE place to point the frontend at your backend.

  LOCAL DEVELOPMENT (default):
    const API_BASE = "http://127.0.0.1:5000";

  PRODUCTION (after you deploy the backend to Render):
    Replace the line below with your real Render URL, e.g.
    const API_BASE = "https://topgrade-backend.onrender.com";

  This file must be loaded BEFORE app.js and chat.js in index.html,
  since both of them use the API_BASE constant defined here.
*/
const API_BASE = "http://127.0.0.1:5000";
