"""
Mediate access to any spansh.co.uk APIs.
"""

import requests

class Spansh:
  """Access to spansh.co.uk APIs."""

  def __init__(self, logger):
    """
    Initialise access to spansh.co.uk APIs.

    :param logger: `logging.Logger` instance.
    """
    self.logger = logger

    self.session = requests.Session()
