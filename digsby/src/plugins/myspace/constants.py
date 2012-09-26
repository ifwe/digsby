class NS:
    ActivityStreams = 'http://activitystrea.ms/schema/1.0/'
    ActivityContext = 'http://activitystrea.ms/context/'
    Atom = 'http://www.w3.org/2005/Atom'
    
class Object:
    Photo = 'http://activitystrea.ms/schema/1.0/photo'
    BlogEntry = 'http://activitystrea.ms/schema/1.0/blog-entry'
    Song = 'http://activitystrea.ms/schema/1.0/song'
    Note = 'http://activitystrea.ms/schema/1.0/note'
    ForumTopic = 'http://activities.myspace.com/schema/1.0/ObjectTypes/Forum_Topic'
    Video = 'http://activitystrea.ms/schema/1.0/video'
    Group = 'http://activitystrea.ms/schema/1.0/group'
    Event = 'http://activitystrea.ms/schema/1.0/event'
    
    Band = 'http://activities.myspace.com/schema/1.0/ObjectTypes/Band'
    Politician = 'http://activities.myspace.com/schema/1.0/ObjectTypes/Politician'
    Comedian = 'http://activities.myspace.com/schema/1.0/ObjectTypes/Comedian'
    Filmmaker = 'http://activities.myspace.com/schema/1.0/ObjectTypes/Filmmaker'
    
    FriendCategory = 'http://activities.myspace.com/schema/1.0/ObjectTypes/Friend_Category'
    
    @classmethod
    def get_name(cls, uri):
        for x in cls.__dict__:
            if cls.__dict__.get(x, None) == uri:
                return x
            
        return 'Unknown'
    
class Verb:
    Tag = 'http://activities.myspace.com/schema/1.0/Verbs/Tag'
    Install = 'http://activities.myspace.com/schema/1.0/Verbs/Install'
    Post = 'http://activitystrea.ms/schema/1.0/post'
    Share = 'http://activitystrea.ms/schema/1.0/share'
    Favorite = 'http://activitystrea.ms/schema/1.0/favorite'
    ConfirmConnection = 'http://activitystrea.ms/schema/1.0/confirm-connection'
    Join = 'http://activitystrea.ms/schema/1.0/join'
    
    @classmethod
    def get_name(cls, uri):
        for x in cls.__dict__:
            if cls.__dict__.get(x, None) == uri:
                return x
            
        return 'Unknown'

BlogPost      = (Verb.Post, Object.BlogEntry)
PhotoPost     = (Verb.Post, Object.Photo)
SongPost      = (Verb.Share, Object.Song)
StatusUpdate  = (Verb.Post, Object.Note) 
ForumTopicPost= (Verb.Post, Object.ForumTopic)
VideoShare    = (Verb.Share, Object.Video)
VideoPost     = (Verb.Post, Object.Video)
VideoFavorite = (Verb.Favorite, Object.Video)