#include "EventLoop.h"
#include "Transaction.h"

void processEvents()
{
    // commit all pending transactions
    Transaction::commitAll();

    // tick all animations
    Animation::tickAll(GetCurrentTimeSeconds());
}

