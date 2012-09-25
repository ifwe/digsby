# Pets newsfeed. Seconday strings are not being used at this point

achievement_strings = {
    'ready_to_play'      : _('Ready To Play'),
    'pets_lover'         : _('Pets Lover'),
    'frequent_shopper'   : _('Frequent Shopper'),
    'perfect_attendance' : _('Perfect Attendance'),
    'successful_tycoon'  : _('Successful Tycoon'),
    'hot_stuff'          : _('Hot Stuff'),
    'big_spender'        : _('Big Spender')
}

newsfeed_strings = [
     { # EARNED
      'primary'   : lambda *a:
            {'string' : _('You earned a %s bonus for signing in to Tagged!'),
             'params' : ['earned_amount']},
      'secondary' : lambda *a:
            {'string' : _('%s earned a %s bonus for signing in to Tagged!'),
             'params' : ['target_link', 'earned_amount']}
  }, { # BOUGHT PET
      'primary'   : lambda event, *a:
            {'string' : _('You bought %s from %s for %s.') if event['owner_id'] else
                        _('You bought %s for %s.'),
             'params' : ['pet_link', 'owner_link', 'purchase_price'] if event['owner_id'] else
                        ['pet_link', 'purchase_price']},
      'secondary' : lambda event, *a:
            {'string' : _('%s bought %s from %s for %s.') if event['owner_id'] else
                        _('%s bought %s for %s.'),
             'params' : ['target_link', 'pet_link', 'owner_link', 'purchase_price'] if event['owner_id'] else
                        ['target_link', 'pet_link', 'purchase_price']}
  }, { # BOUGHT YOU
      'primary'   : lambda *a:
            {'string' : _('%s bought you for %s earning you %s.'),
             'params' : ['owner_link', 'purchase_price', 'earned_amount']},
      'secondary' : lambda event, *a:
            {'string' : _('%s bought %s for %s earning %s %s.') if event.earned_amount else
                        _('%s bought %s for %s.'),
             'params' : ['owner_link', 'target_link', 'purchase_price', 'target_link', 'earned_amount'] if event.earned_amount else
                        ['owner_link', 'target_link', 'purchase_price']}
  }, { # BOUGHT YOUR PET
      'primary'   : lambda *a:
            {'string' : _('%s bought your pet %s for %s earning you %s (%s profit).'),
             'params' : ['owner_link', 'pet_link', 'purchase_price', 'earned_amount', 'profit_amount']},
      'secondary' : lambda *a:
            {'string' : _("%s bought %s's pet %s for %s earning %s %s (%s profit)."),
             'params' : ['owner_link', 'target_link', 'pet_link', 'purchase_price' 'target_link', 'earned_amount', 'profit_amount']}
  }, { # PET WAS SET FREE
      'primary'   : lambda *a:
            {'string' : _('Your pet %s was set free for %s earning you %s (%s profit).'),
             'params' : ['pet_link', 'setfree_price', 'earned_amount', 'profit_amount']},
      'secondary' : lambda *a:
            {'string' : _("%s's pet %s was set free for %s earning %s %s (%s profit)."),
             'params' : ['target_link', 'pet_link', 'setfree_price', 'target_link', 'earned_amount', 'profit_amount']}
  }, { # WERE SET FREE
      'primary'   : lambda *a:
            {'string' : _('%s set you free.'),
             'params' : ['owner_link']},
      'secondary' : lambda *a:
            {'string' : _('%s set %s free.'),
             'params' : ['owner_link', 'target_link']}
  }, { # SET SELF FREE
      'primary'   : lambda *a:
            {'string' : _('You set yourself free from %s for %s.'),
             'params' : ['owner_link', 'setfree_price']},
      'secondary' : lambda *a:
            {'string' : _('%s set %s free from %s for %s.'),
             'params' : ['owner_link', 'gender', 'owner_link', 'setfree_price']}
  }, { # SET PET FREE
      'primary'   : lambda *a:
            {'string' : _('You set %s free.'),
             'params' : ['pet_link']},
      'secondary' : lambda *a:
            {'string' : _('%s set %s free.'),
             'params' : ['target_link', 'pet_link']}
  }, { # FIRST TO OWN
      'primary'   : lambda *a:
            {'string' : _('You bought %s for %s and earned a %s bonus for being the first owner.'),
             'params' : ['pet_link', 'purchase_price', 'bonus_price']},
      'secondary' : lambda *a:
            {'string' : _('%s bought %s for %s and earned a %s bonus for being the first owner.'),
             'params' : ['target_link', 'pet_link', 'purchase_price', 'bonus_price']}
  }, { # PET WAS DELETED
      'primary'   : lambda *a:
            {'string' : _('%s has been deleted so you have been credited %s.'),
             'params' : ['pet_name', 'refund_amount']},
      'secondary' : lambda *a:
            {'string' : _('%s has been deleted so %s has been credited %s.'),
             'params' : ['pet_name', 'target_link', 'refund_amount']}
  }, { # BONUS FROM BUYING PET
      'primary'   : lambda *a:
            {'string' : _('You earned %s bonus after buying %s.'),
             'params' : ['bonus_amount', 'pet_link']},
      'secondary' : lambda *a:
            {'string' : _('%s earned %s bonus after buying %s.'),
             'params' : ['owner_link', 'bonus_amount', 'pet_link']}
  }, { # EARNED ACHIEVEMENT
      'primary'   : lambda *a:
            {'string' : _('You earned a "%s" achievement!'),
             'params' : ['achievement_name']},
      'secondary' : lambda *a:
            {'string' : _('%s earned a "%s" achievement!'),
             'params' : ['target_link', 'achievement_name']}
  }, { # BOUGHT AND COLLECTED PURCHASE BONUS
      'primary'   : lambda event, *a:
            {'string' : _('You bought %s from %s for %s and earned a %s bonus.') if event.owner_id else
                        _('You bought %s for %s and earned a %s bonus.'),
             'params' : ['pet_link', 'owner_link', 'purchase_price', 'bonus_amount'] if event.owner_id else
                        ['pet_link', 'purchase_price', 'bonus_amount']},
      'secondary' : lambda event, *a:
            {'string' : _('%s bought %s from %s for %s and earned a %s bonus.') if event.owner_id else
                        _('%s bought %s for %s and earned a %s bonus.'),
             'params' : ['target_link', 'pet_link', 'owner_link', 'purchase_price', 'bonus_amount'] if event.owner_id else
                        ['target_link', 'pet_link', 'purchase_price', 'bonus_amount']}
  }, { # UNLOCKED NEWSFEED
      'primary'   : lambda *a:
            {'string' : _('You activated your newsfeed!'),
             'params' : []},
      'secondary' : lambda *a:
            {'string' : _('%s activated their newsfeed!'),
             'params' : ['target_link']}
  }]
