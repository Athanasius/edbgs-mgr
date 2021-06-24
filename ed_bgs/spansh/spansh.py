"""
Mediate access to any spansh.co.uk APIs.
"""

import requests

class Spansh:
  """Access to spansh.co.uk APIs."""
  TOURIST_URL = 'https://www.spansh.co.uk/api/tourist/route'

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
    data = f'source={start}&range={range}&loop={int(loop)}'
    for s in systems:
      data += f'&destination={requests.utils.requote_uri(s)}'

    self.logger.info(f'data for tourist route query:\n{data}\n')
