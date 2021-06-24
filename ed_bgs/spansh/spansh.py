"""
Mediate access to any spansh.co.uk APIs.
"""

import requests

class Spansh:
  """Access to spansh.co.uk APIs."""
  TOURIST_URL = 'https://www.spansh.co.uk/api/tourist/route'
  TOURIST_RESULT_PREFIX = 'https://www.spansh.co.uk/tourist/results/'

  def __init__(self, logger):
    """
    Initialise access to spansh.co.uk APIs.

    :param logger: `logging.Logger` instance.
    """
    self.logger = logger

    self.session = requests.Session()

  def tourist_route(self, start: str, range: float, systems: list, loop: bool = False) -> str:
    """
    Ask for a Tourist Route around the specified systems.

    :param start: `str` - name of starting system.
    :param range: `float` - ship laden jump range.
    :param systems: `list` of `str` - system names to route around.
    :param loop: `bool` - Whether to force the route to return to the start system.
    :returns: `str` - spansh.co.uk results URL.
    """
    # We can't use a dict for this as we'll need to supply multiple
    # `destination` members.
    data = [
      ('source', start),
      ('range', range),
      ('loop', int(loop)),
    ]
    for s in systems:
      data.append(
        ('destination', s)
      )

    # self.logger.debug(f'data for tourist route query:\n{data}\n')

    try:
      r = self.session.post(
				self.TOURIST_URL,
        data,
      )

    except requests.exceptions.HTTPError as e:
      self.logger.warning(f'Error requesting the route: {e!r}')
      return None

    # self.logger.debug(f'Returned data:\n{r.content.decode()}\n')

    try:
      answer = r.json()

    except json.JSONDecodeError as e:
      self.logger.warning(f'Error decoding JSON for answer: {e!r}')
      return None

    if answer.get('error', False):
      self.logger.warning(f'spansh.co.uk replied with an error: {answer["error"]}')
      return None

    if not (status := answer.get('status', False)):
      self.logger.warning(f"No error, but spansh.co.uk didn't give a status either:\n{r.content.decode()}\n")
      return None

    if status != 'queued':
      self.logger.warning(f"spansh.co.uk gave a status other than queued:\n{r.content.decode()}\n")
      return None

    job = answer.get('job')
    if job is None:
      self.logger.warning(f"spansh.co.uk said 'queued', but gave no job ID:\n{r.content.decode()}\n")
      return None

    return f'{self.TOURIST_RESULT_PREFIX}{job}'
