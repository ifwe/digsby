
#include <gtest/gtest.h>
#include "RingBuffer.h"

class CGUITest : public testing::Test
{
protected:
    virtual ~CGUITest() {}
};

#define EQ_BUFFER(ringbuffer_, ...) \
    { \
    static const int expected[] = { __VA_ARGS__ }; \
    int len_ = sizeof(expected) / sizeof(int); \
    int* _temp_buffer = (int*)malloc(sizeof(int) * len_); \
    ringbuffer_.data(_temp_buffer); \
    ASSERT_EQ(0, memcmp(_temp_buffer, &expected, len_)); \
    delete _temp_buffer; \
    }

    

TEST_F(CGUITest, TestRingBuffer)
{
    RingBuffer<int, 5> b;
    b.append(3);
    EQ_BUFFER(b, 3);
    ASSERT_EQ(1, b.size());

    RingBuffer<int, 1> b2;
    b2.append(5);
    EQ_BUFFER(b2, 5, 1);    
    b2.append(6);
    EQ_BUFFER(b2, 6, 1);
    b2.append(7);
    EQ_BUFFER(b2, 7);
    ASSERT_EQ(1, b2.size());
    
    RingBuffer<int, 3> b3;
    b3.append(42); b3.append(42); b3.append(42);
    ASSERT_EQ(3, b3.size());
    b3.append(50);
    ASSERT_EQ(3, b3.size());
    EQ_BUFFER(b3, 42, 42, 50);
    b3.append(60);
    EQ_BUFFER(b3, 42, 50, 60);
    b3.append(70);
    EQ_BUFFER(b3, 50, 60, 70);
    ASSERT_EQ(3, b3.size());
}
