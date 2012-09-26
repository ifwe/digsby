#include "Animation.h"

#include <gtest/gtest.h>

class LayerTest : public testing::Test
{
protected:
    virtual void SetUp()
    {
        layer = new Layer();
        sublayer = new Layer(layer);
    }

    virtual void TearDown()
    {
        delete l;
    }

    Layer* l;
};

TEST_F(LayerTest, SetPosition)
{
    l->setPosition(50.0, 80.0);
    Point p = l->position();
    EXPECT_EQ(50.0, p.x);
    EXPECT_EQ(80.0, p.y);
}

TEST_F(LayerTest, SetSpeed)
{
    sublayer->setSpeed(2.0f);
    layer->setSpeed(3.0f);
    
    EXPECT_EQ(6.0f, sublayer->effectiveSpeed());
    EXPECT_EQ(3.0f, layer->effectiveSpeed());

    EXPECT_EQ(2.0f, sublayer->speed());
    EXPECT_EQ(3.0f, layer->speed());
}
