src/mailerlite.py (new file):

  """
  MailerLite integration — adds new registrants to a mailing list group.
  API: MailerLite v2 (connect.mailerlite.com)
  """
  import os
  import logging
  import requests

  logger = logging.getLogger(__name__)

  MAILERLITE_API_KEY = os.environ.get("MAILERLITE_API_KEY", "")
  MAILERLITE_GROUP_ID = os.environ.get("MAILERLITE_GROUP_ID", "")  # your list/group ID


  def add_subscriber(email: str, name: str) -> bool:
      """
      Add a new user to the MailerLite mailing list.
      Returns True on success, False on any failure (never raises).
      """
      if not MAILERLITE_API_KEY:
          logger.warning("MAILERLITE_API_KEY not set — skipping subscriber add")
          return False

      payload = {
          "email": email,
          "fields": {"name": name},
          "status": "active",
      }
      if MAILERLITE_GROUP_ID:
          payload["groups"] = [MAILERLITE_GROUP_ID]

      try:
          resp = requests.post(
              "https://connect.mailerlite.com/api/subscribers",
              json=payload,
              headers={
                  "Authorization": f"Bearer {MAILERLITE_API_KEY}",
                  "Content-Type": "application/json",
                  "Accept": "application/json",
              },
              timeout=5,
          )
          if resp.status_code in (200, 201):
              logger.info(f"MailerLite: added {email} to mailing list")
              return True
          else:
              logger.error(f"MailerLite: failed to add {email} — {resp.status_code} {resp.text}")
              return False
      except Exception as e:
          logger.error(f"MailerLite: exception adding {email} — {e}")
          return False