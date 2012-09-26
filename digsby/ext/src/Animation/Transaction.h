#ifndef Animation_Transaction_h
#define Animation_Transaction_h

#include "Animation.h"
#include "Layer.h"

#include <stack>
using std::stack;
using std::pair;

class Transaction;

typedef stack<Transaction*> TransactionStack;

class ImplicitTransaction;

class Transaction
{
public:
    static void begin();
    static void commit();
    static void commitAll();
    static Transaction* implicit();

    static void setAnimationDuration(Time animationDuration);
    static Time animationDuration();

    static void setDisableActions(bool disableActions);
    static bool disableActions();

    bool isImplicit() const { return m_implicit; }

protected:
    friend class ImplicitTransaction;

    void addAnimation(Layer*, AnimationKeyPath animationKeyPath);
    AnimationMap* animationMapForLayer(Layer* layer);

    static TransactionStack ms_transactions;

    static Transaction* active()
    {
        ANIM_ASSERT(!ms_transactions.empty());
        return ms_transactions.top();
    }

    //
    // non-static members
    //
    Transaction(bool implicit = false);
    ~Transaction();

    Time _animationDuration() const { return m_animationDuration; }
    void _setAnimationDuration(Time animationDuration);

    bool _disableActions() const { return m_disableActions; }
    void _setDisableActions(bool disableActions);

    void _commit();

    Time m_animationDuration;
    vector<pair<AnimationKeyPath, Layer*>> m_pendingAnimations;
    bool m_implicit:1;
    bool m_disableActions:1;
};

class ImplicitTransaction
{
public:
    ImplicitTransaction(Layer* layer, AnimationKeyPath animationKeyPath);
    ~ImplicitTransaction() {}

    Transaction* transaction() const { return m_transaction; } 
protected:

    Transaction* m_transaction;
};


#endif // Animation_Transaction_h

