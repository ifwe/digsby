# Elections newsfeed. Seconday strings are not being used at this point

newsfeed_strings = [
     { # VOTED
      'primary'   : {'string' : _('You voted "%s" for %s'),
                     'params' : ['issue_vote', 'issue_title']},
      'secondary' : {'string' : _('%s voted "%s" for %s'),
                     'params' : ['displayname', 'issue_vote', 'issue_title']}
  }, { # ADDED STAFF
      'primary'   : {'string' : _('You hired %s'),
                     'params' : ['target_name']},
      'secondary' : {'string' : _('%s hired %s'),
                     'params' : ['displayname', 'target_name']}
  }, { # ADDED AS STAFF
      'primary'   : {'string' : _('%s hired you'),
                     'params' : ['target_name']},
      'secondary' : {'string' : _('%s hired %s'),
                     'params' : ['target_name', 'displayname']},
  }, { # STARTED PROJECT
      'primary'   : {'string' : _('You started the project "%s"'),
                     'params' : ['project_title']},
      'secondary' : {'string' : _('%s started the project "%s"'),
                     'params' : ['displayname', 'project_title']}
  }, { # CONTRIBUTED
      'primary'   : {'string' : _('You contributed to the project "%s"'),
                     'params' : ['project_title']},
      'secondary' : {'string' : _('%s contributed to the project "%s"'),
                     'params' : ['displayname', 'project_title']}
  }, { # PROJECT COMPLETED
      'primary'   : {'string' : _('Project "%s" completed'),
                     'params' : ['project_title']},
      'secondary' : {'string' : _('Project "%s" completed'),
                     'params' : ['project_title']}
  }, { # EARNED FAME
      'primary'   : {'string' : _('You earned %s Fame from completing Project "%s"'),
                     'params' : ['fame', 'project_title']},
      'secondary' : {'string' : _('%s earned %s Fame from completing Project "%s"'),
                     'params' : ['displayname', 'fame', 'project_title']}
  }, { # GOT COLLABORATORS
      'primary'   : {'string' : _('You gained %s new collaborators'),
                     'params' : ['collaborators']},
      'secondary' : {'string' : _('%s gained %s new collaborators'),
                     'params' : ['displayname', 'collaborators']}
  }, { # EARNED VOTES
      'primary'   : {'string' : _('Your party gained %s votes'),
                     'params' : ['votes']},
      'secondary' : {'string' : _('%s gained %s votes'),
                     'params' : ['party', 'votes']}
  }, { # GAVE FAVOR
      'primary'   : {'string' : _('You gave %s a favor'),
                     'params' : ['target_name']},
      'secondary' : {'string' : _('%s gave %s a favor'),
                     'params' : ['displayname', 'target_name']}
  }, { # GOT FAVOR
      'primary'   : {'string' : _('%s did a favor for you'),
                     'params' : ['target_name']},
      'secondary' : {'string' : _('%s did a favor for %s'),
                     'params' : ['target_name', 'displayname']}
  }, { # THANKED
      'primary'   : {'string' : _('You thanked %s'),
                     'params' : ['target_name']},
      'secondary' : {'string' : _('%s thanked %s'),
                     'params' : ['displayname', 'target_name']}
  }, { # GOT THANKED
      'primary'   : {'string' : _('%s thanked you'),
                     'params' : ['target_name']},
      'secondary' : {'string' : _('%s thanked %s'),
                     'params' : ['target_name', 'displayname']}
  }, { # LEVELED UP
      'primary'   : {'string' : _('You leveled up'),
                     'params' : []},
      'secondary' : {'string' : _('%s leveled up'),
                     'params' : ['displayname']}
  }, { # JOINED PARTY
      'primary'   : {'string' : _('You joined the %s party'),
                     'params' : ['party']},
      'secondary' : {'string' : _('%s joined the %s party'),
                     'params' : ['displayname', 'party']}
  }, { # PARTY CAPTAIN
      'primary'   : {'string' : _('You became a Party Captain'),
                     'params' : []},
      'secondary' : {'string' : _('%s became a Party Captain'),
                     'params' : ['displayname']}
  }, { # PARTY LEADER
      'primary'   : {'string' : _('You became a Party Leader'),
                     'params' : []},
      'secondary' : {'string' : _('%s became a Party Leader'),
                     'params' : ['displayname']}
  }, { # PROJECT FAILED
      'primary'   : {'string' : _('The "%s" you contributed to was unable to get fully funded'),
                     'params' : ['project_title']},
      'secondary' : {'string' : _('The "%s" %s contributed to was unable to get fully funded'),
                     'params' : ['project_title', 'displayname']}
  }, { # GOT NEW COLLABORATORS
      'primary'   : {'string' : _('You earned %s new Collaborators from completing "%s"'),
                     'params' : ['collaborators', 'project_title']},
      'secondary' : {'string' : _('%s earned %s new Collaborators from completing "%s"'),
                     'params' : ['displayname', 'collaborators', 'project_title']}
  }, { # GOT FAVOR BONUS
      'primary'   : {'string' : _('%s called in a Favor for your Staff Job earning you a bonus of %s funds'),
                     'params' : ['target_name', 'funds']},
      'secondary' : {'string' : _('%s called in a Favor for %s\'s Staff Job earning them a bonus of %s funds'),
                     'params' : ['target_name', 'displayname', 'funds']}
  }, { # GOT THANKED BONUS
      'primary'   : {'string' : _('%s thanked you for your Favor earning you a bonus of %s Fame'),
                     'params' : ['target_name', 'fame']},
      'secondary' : {'string' : _('%s thanked %s for their Favor, earning them a bonus of %s Fame'),
                     'params' : ['target_name', 'displayname', 'fame']}
  }, { # GOT STARTING FUNDS
      'primary'   : {'string' : _('You received %s funds for the new Election!'),
                     'params' : ['funds']},
      'secondary' : {'string' : _('%s received %s funds for the new Election!'),
                     'params' : ['displayname', 'funds']}
  }, { # THANKED BONUS
      'primary'   : {'string' : _('You thanked %s for calling in a favor, earning you a bonus of %s funds'),
                     'params' : ['target_name', 'funds']},
      'secondary' : {'string' : _('%s thanked %s for calling in a favor, earning them a bonus of %s funds'),
                     'params' : ['displayname', 'target_name', 'funds']},
  }]