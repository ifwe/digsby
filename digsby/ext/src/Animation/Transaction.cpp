#include "Layer.h"
#include "Transaction.h"

TransactionStack Transaction::ms_transactions;

Transaction::Transaction(bool implicit)
    : m_disableActions(false)
    , m_animationDuration(0.0)
    , m_implicit(implicit)
{
}

Transaction::~Transaction()
{
}

Transaction* Transaction::implicit()
{
    if (ms_transactions.empty())
        ms_transactions.push(new Transaction(true));

    return ms_transactions.top();
}

void Transaction::begin()
{
    Transaction* transaction = new Transaction(false);
    ms_transactions.push(transaction);
}

void Transaction::commit()
{
    ANIM_ASSERT(ms_transactions.size() > 0);

    Transaction* transaction = ms_transactions.top();
    transaction->_commit();
    ms_transactions.pop();
}

void Transaction::commitAll()
{
    while (ms_transactions.size())
        Transaction::commit();
}

void Transaction::setAnimationDuration(Time animationDuration)
{
    active()->_setAnimationDuration(animationDuration);
}

Time Transaction::animationDuration()
{
    return active()->_animationDuration();
}


//
// non-static member functions
//

void Transaction::_setAnimationDuration(Time animationDuration)
{
    m_animationDuration = animationDuration;
}

void Transaction::_setDisableActions(bool disableActions)
{
    m_disableActions = disableActions;
}

void Transaction::_commit()
{
    for (size_t i = 0; i < m_pendingAnimations.size(); ++i) {
        const pair<AnimationKeyPath, Layer*>& animPair = m_pendingAnimations[i];

        AnimationKeyPath animationKeyPath = animPair.first;
        Layer* layer = animPair.second;

        Animation::defaultAnimation(animationKeyPath, layer);
    }
}

AnimationMap* Transaction::animationMapForLayer(Layer* layer)
{
}

void Transaction::addAnimation(Layer* layer, AnimationKeyPath animationKeyPath)
{
    m_pendingAnimations.push_back(pair<AnimationKeyPath, Layer*>(animationKeyPath, layer));
}

ImplicitTransaction::ImplicitTransaction(Layer* layer, AnimationKeyPath animationKeyPath)
{
    m_transaction = Transaction::implicit();
    m_transaction->addAnimation(layer, animationKeyPath);
}

