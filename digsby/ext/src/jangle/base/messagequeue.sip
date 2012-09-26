namespace talk_base {

// MessageQueueManager does cleanup of of message queues

class MessageQueueManager {

%TypeHeaderCode
#include "talk/base/messagequeue.h"
%End

public:
  static talk_base::MessageQueueManager* Instance();

  void Add(talk_base::MessageQueue *message_queue);
  void Remove(talk_base::MessageQueue *message_queue);
  void Clear(talk_base::MessageHandler *handler);

private:
  MessageQueueManager();
  ~MessageQueueManager();
/*
  static MessageQueueManager* instance_;
  // This list contains 'active' MessageQueues.
  std::vector<MessageQueue *> message_queues_;
  CriticalSection crit_;
*/
};

// Messages get dispatched to a MessageHandler

class MessageHandler {

%TypeHeaderCode
#include "talk/base/messagequeue.h"
%End

public:
  virtual ~MessageHandler();

  virtual void OnMessage(talk_base::Message *pmsg) = 0;
};

// Derive from this for specialized data
// App manages lifetime, except when messages are purged

class MessageData {

%TypeHeaderCode
#include "talk/base/messagequeue.h"
%End

public:
  MessageData();
  virtual ~MessageData();
};
/*
template <class T>
class TypedMessageData : public MessageData {
public:
  TypedMessageData(const T& data) : data_(data) { }
  const T& data() const { return data_; }
  T& data() { return data_; }
private:
  T data_;
};

template<class T>
inline MessageData* WrapMessageData(const T& data) {
  return new TypedMessageData<T>(data);
}

template<class T>
inline const T& UseMessageData(MessageData* data) {
  return static_cast< TypedMessageData<T>* >(data)->data();
}

template<class T>
class DisposeData : public MessageData {
public:
  DisposeData(T* data) : data_(data) { }
  virtual ~DisposeData() { delete data_; }
private:
  T* data_;
};
*/

const uint32 MQID_ANY;
const uint32 MQID_DISPOSE;

// No destructor

struct Message {
  Message();
  talk_base::MessageHandler *phandler;
  uint32 message_id;
  talk_base::MessageData *pdata;
  uint32 ts_sensitive;
};

// DelayedMessage goes into a priority queue, sorted by trigger time

class DelayedMessage {

%TypeHeaderCode
#include "talk/base/messagequeue.h"
%End


public:
  DelayedMessage(int cmsDelay, talk_base::Message *pmsg);

  bool operator< (const talk_base::DelayedMessage& dmsg) const;

  int cmsDelay_; // for debugging
  uint32 msTrigger_;
  talk_base::Message msg_;
};

class MessageQueue {

%TypeHeaderCode
#include "talk/base/messagequeue.h"
%End

public:
  MessageQueue(talk_base::SocketServer* ss = 0);
  virtual ~MessageQueue();

  talk_base::SocketServer* socketserver();
  void set_socketserver(talk_base::SocketServer* ss);

  // Note: The behavior of MessageQueue has changed.  When a MQ is stopped,
  // futher Posts and Sends will fail.  However, any pending Sends and *ready*
  // Posts (as opposed to unexpired delayed Posts) will be delivered before
  // Get (or Peek) returns false.  By guaranteeing delivery of those messages,
  // we eliminate the race condition when an MessageHandler and MessageQueue
  // may be destroyed independently of each other.

  virtual void Stop();
  virtual bool IsStopping();
  virtual void Restart();

  // Get() will process I/O until:
  //  1) A message is available (returns true)
  //  2) cmsWait seconds have elapsed (returns false)
  //  3) Stop() is called (returns false)
  virtual bool Get(talk_base::Message *pmsg, int cmsWait = talk_base::kForever);
  virtual bool Peek(talk_base::Message *pmsg, int cmsWait = 0);
  virtual void Post(talk_base::MessageHandler *phandler, uint32 id = 0,
      talk_base::MessageData *pdata = NULL, bool time_sensitive = false);
  virtual void PostDelayed(int cmsDelay, talk_base::MessageHandler *phandler,
      uint32 id = 0, talk_base::MessageData *pdata = NULL);
  virtual void Clear(talk_base::MessageHandler *phandler, uint32 id = talk_base::MQID_ANY);
  virtual void Dispatch(talk_base::Message *pmsg);
  virtual void ReceiveSends();
  virtual int GetDelay();

  // Internally posts a message which causes the doomed object to be deleted
  //template<class T> void Dispose(T* doomed);

protected:
  void EnsureActive();
/*
  SocketServer* ss_;
  bool new_ss;
  bool fStop_;
  bool fPeekKeep_;
  Message msgPeek_;
  // A message queue is active if it has ever had a message posted to it.
  // This also corresponds to being in MessageQueueManager's global list.
  bool active_;
  std::queue<Message> msgq_;
  std::priority_queue<DelayedMessage> dmsgq_;
  CriticalSection crit_;
*/
};

}; // namespace talk_base