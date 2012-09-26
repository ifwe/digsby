#include "precompiled.h"
#include <gtest/gtest.h>
#include <memory>
#include <vector>
#include <string>
using std::wstring;
using std::auto_ptr;
using std::vector;

#include "config.h"
#include "BuddyListSorter.h"
#include "Sorters.h"
#include "Group.h"
#include "Node.h"
#include "Comparators.h"
#include "StringUtils.h"
#include "BuddyListSorterPrivate.h"
#include "merge.h"
#include "bisect.h"

#include "MemLeakCheckingTest.h"

#if defined(WIN32) && defined(_DEBUG)
#define TEST_FIXTURE_BASE Win32MemLeakCheckingTest
#else
#define TEST_FIXTURE_BASE testing::Test
#endif

class SorterTest : public TEST_FIXTURE_BASE
{
protected:
    virtual ~SorterTest() {}
};

typedef auto_ptr<Group> GroupPtr;
typedef auto_ptr<Node> NodePtr;

static BuddyListSorter* newSorter()
{
    BuddyListSorter* sorter = new BuddyListSorter();
    sorter->addSorter(new ByGroup(false));
    sorter->addSorter(new ByStatus(true));
    return sorter;
}

TEST_F(SorterTest, CanCreate)
{
    // Check that we can instantiate a sorter.
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
}

TEST_F(SorterTest, MergesGroups)
{
    auto_ptr<BuddyListSorter> sorter(newSorter());

    // Check that two subgroups with the same name are merged.
    GroupPtr g(new Group(L"root"));
    Group* c1 = new Group(L"subroot");
    Group* c2 = new Group(L"subroot");

    g->addChild(c1);
    g->addChild(c2);
    sorter->setRoot(g.get());

    Node* n = sorter->root();
    ASSERT_EQ(n->data()->name(), g->name());
    ASSERT_EQ(n->numChildren(), 1);
}

TEST_F(SorterTest, MergesGroups2)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByGroup(true, 2));

    // Check that two subgroups with the same name are merged.
    GroupPtr root(new Group(L"Root"));
    Group* ga = new Group(L"root1");
    Group* gb = new Group(L"root2");
    Group* gc = new Group(L"root3");
    Group* g1 = new Group(L"subroot");
    Group* g2 = new Group(L"subroot");
    Group* g3 = new Group(L"subroot");
    Buddy* b1 = sorter->account(L"digsby01", L"aim")->buddy(L"buddy1");
    Buddy* b2 = sorter->account(L"digsby01", L"gtalk")->buddy(L"buddy2");
    Buddy* b3 = sorter->account(L"digsby01", L"digsby")->buddy(L"buddy3");

    ga->addChild(g1);
    gb->addChild(g2);
    gc->addChild(g3);
    root->addChild(ga);
    root->addChild(gb);
    root->addChild(gc);

    g1->addChild(b1);
    g2->addChild(b2);
    g3->addChild(b3);

    sorter->setRoot(root.get());

    NodePtr n(sorter->gather());
    ASSERT_EQ(n->data()->name(), root->name());
    ASSERT_EQ(1, n->numChildren());
    ASSERT_TRUE(n->children()[0]->data()->asGroup());
    ASSERT_EQ(3, n->children()[0]->numChildren());
    ASSERT_TRUE(n->children()[0]->children()[0]->data()->asContact());
    ASSERT_TRUE(n->children()[0]->children()[1]->data()->asContact());
    ASSERT_TRUE(n->children()[0]->children()[2]->data()->asContact());
}

TEST_F(SorterTest, MergesGroupsCaseInsensitive)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByGroup(true, 2));

    // Check that two subgroups with the same name (case insensitive) are merged.
    GroupPtr g(new Group(L"root"));
    Group* r1 = new Group(L"subroot");
    Group* r2 = new Group(L"subroot2");
    Group* r3 = new Group(L"subroot3");
    Group* r4 = new Group(L"subroot4");

    // Lots of groups with different case
    Group* dotsyntax1 = new Group(L"dotsyntax");
    Group* dotsyntax2 = new Group(L"dotSyntax");
    Group* dotsyntax3 = new Group(L"dOTSyntaX");
    Group* dotsyntax4 = new Group(L"dotsyntax");

    Buddy* b1 = sorter->account(L"digsby01", L"aim")->buddy(L"buddy1");
    Buddy* b2 = sorter->account(L"digsby01", L"gtalk")->buddy(L"buddy2");

    dotsyntax1->addChild(b1);
    dotsyntax2->addChild(b2);
    r1->addChild(dotsyntax1);
    r2->addChild(dotsyntax2);
    r3->addChild(dotsyntax3);
    r4->addChild(dotsyntax4);
    g->addChild(r1); g->addChild(r2); g->addChild(r3); g->addChild(r4);
    sorter->setRoot(g.get());

    NodePtr n(sorter->gather());
    ASSERT_EQ(1, n->numChildren());

    Node* groupNode = n->children()[0];

    // The most-cased group name should be the one we see.
    EXPECT_EQ(L"dOTSyntaX", groupNode->name());
    ASSERT_EQ(2, groupNode->numChildren());

    ASSERT_TRUE(groupNode->data());
}

TEST_F(SorterTest, DoesNotMergeGroups)
{
    auto_ptr<BuddyListSorter> sorter(newSorter());

    // Check that two subgroups with different names are not merged.
    GroupPtr g(new Group(L"root"));
    g->addChild(new Group(L"subroot1"));
    g->addChild(new Group(L"subroot2"));
    sorter->setRoot(g.get());

    Node* n = sorter->root();
    ASSERT_EQ(n->data()->name(), g->name());
    ASSERT_EQ(n->numChildren(), 2);
    ASSERT_EQ(n->children()[0]->data()->name(), g->children()[0]->name());
}


TEST_F(SorterTest, TestContactAttributes)
{
    auto_ptr<BuddyListSorter> sorter(newSorter());

    Buddy* b = sorter->account(L"digsby01", L"aim")->buddy(L"digsby03");

    // Check that two subgroups with different names are not merged.
    GroupPtr g(new Group(L"root"));
    g->addChild(new Group(L"subroot1"));
    g->addChild(new Group(L"subroot2"));
    sorter->setRoot(g.get());

    Node* n = sorter->root();
    ASSERT_EQ(n->data()->name(), g->name());
    ASSERT_EQ(n->numChildren(), 2);
    ASSERT_EQ(n->children()[0]->data()->name(), g->children()[0]->name());
}

TEST_F(SorterTest, GroupByService)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByGroup(true));
    sorter->addSorter(new ByService(true));

    GroupPtr g(new Group(L"root"));
    Buddy* b = sorter->account(L"digsby01", L"aim")->buddy(L"digsby03");
    g->addChild(b);
    sorter->setRoot(g.get());

    // Check that the ByService group successfully puts buddies into groups
    // based on service.
    NodePtr root(sorter->gather());
    ASSERT_EQ(root->numChildren(), 1);
    Node* serviceGroup = root->children()[0];
    ASSERT_EQ(serviceGroup->key(), L"aim");
    ASSERT_EQ(serviceGroup->numChildren(), 1);
    ASSERT_EQ(serviceGroup->children()[0]->data(), b->contact());
}

TEST_F(SorterTest, TestFilterOffline)
{
    // Ensure that ByOnline can filter offline buddies.
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByGroup(true));
    sorter->addSorter(new ByOnline(false, false));

    GroupPtr g(new Group(L"root"));
    Buddy* b = sorter->account(L"digsby01", L"aim")->buddy(L"digsby01");
    g->addChild(b);

    sorter->setRoot(g.get());

    NodePtr root(sorter->gather());
    ASSERT_EQ(0, root->numChildren());
}

TEST_F(SorterTest, TestMulti)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    Account* acct = sorter->account(L"digsby01", L"aim");

    // Make a MultiComparator that sorts Contact objects first by log size,
    // then by name.
    vector<SortBy> sorts;
    sorts.push_back(LogSize);
    sorts.push_back(Name);
    MultiComparator<const Node*> multi(sorts);

    Buddy* b1 = acct->buddy(L"small_logs"); b1->setLogSize(500);
    Buddy* b2 = acct->buddy(L"big_logs2");  b2->setLogSize(1500);
    Buddy* b3 = acct->buddy(L"big_logs");   b3->setLogSize(1500);

    NodePtr n1(new Node(b1->contact(), NULL));
    NodePtr n2(new Node(b2->contact(), NULL));
    NodePtr n3(new Node(b3->contact(), NULL));

    vector<const Node*> contacts;
    contacts.push_back(n1.get());
    contacts.push_back(n2.get());
    contacts.push_back(n3.get());
    std::sort(contacts.begin(), contacts.end(), multi);

    ASSERT_EQ(contacts[0]->data(), b3->contact());
    ASSERT_EQ(contacts[1]->data(), b2->contact());
    ASSERT_EQ(contacts[2]->data(), b1->contact());

    contacts.clear();
    contacts.push_back(n2.get());
    contacts.push_back(n3.get());
    contacts.push_back(n1.get());
    std::sort(contacts.begin(), contacts.end(), multi);

    ASSERT_EQ(contacts[0]->data(), b3->contact());
    ASSERT_EQ(contacts[1]->data(), b2->contact());
    ASSERT_EQ(contacts[2]->data(), b1->contact());
}


TEST_F(SorterTest, SortByLogSize)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByGroup(true));

    vector<SortBy> sorts;
    sorts.push_back(LogSize);
    sorts.push_back(Name);
    sorter->setComparators(sorts);

    EXPECT_TRUE(sorter->sortsBy(Name));
    EXPECT_TRUE(sorter->sortsBy(LogSize));
    EXPECT_FALSE(sorter->sortsBy(Service));

    Buddy* b1 = sorter->account(L"digsby01", L"aim")->buddy(L"digsby01");
    b1->setLogSize(500);

    Buddy* b2 = sorter->account(L"digsby01", L"aim")->buddy(L"digsby02");
    b2->setLogSize(700);
    EXPECT_EQ(b2->contact()->logSize(), 700);

    Buddy* b3 = sorter->account(L"digsby01", L"aim")->buddy(L"digsby03");
    b3->setLogSize(500);
    EXPECT_EQ(b3->contact()->logSize(), 500);

    GroupPtr r(new Group(L"root"));
    r->addChild(b1);
    r->addChild(b2);
    r->addChild(b3);
    sorter->setRoot(r.get());
    NodePtr root(sorter->gather());

    EXPECT_EQ(3, root->numChildren());

    EXPECT_EQ(700, root->children()[0]->data()->asContact()->logSize());
    EXPECT_EQ(b2->contact(), root->children()[0]->data());
    EXPECT_EQ(b1->contact(), root->children()[1]->data()->asContact());
}

TEST_F(SorterTest, SortByCustomOrder)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByGroup(true));
    sorter->addSorter(new ByOnline(true, true));

    GroupPtr root(new Group(L"root"));
    Group* buddies = new Group(L"buddies");
    Buddy* buddy = sorter->account(L"digsby01", L"aim")->buddy(L"digsby01");
    buddies->addChild(buddy);
    root->addChild(buddies);

    sorter->setRoot(root.get());
    NodePtr n(sorter->gather());
    ASSERT_EQ(2, n->numChildren());
    ASSERT_EQ(buddies->name(), n->children()[0]->data()->name());
    ASSERT_EQ(L"Offline", n->children()[1]->name());
}

TEST_F(SorterTest, TestOfflineFiltering)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByGroup(true));
    sorter->addSorter(new ByOnline(false, false));

    GroupPtr root(new Group(L"root"));

    Buddy* onlineBuddy = sorter->account(L"digsby01", L"aim")->buddy(L"digsby01");
    onlineBuddy->setStatus(L"away");
    Buddy* offlineBuddy = sorter->account(L"digsby01", L"aim")->buddy(L"digsby13");
    offlineBuddy->setStatus(L"offline");

    root->addChild(onlineBuddy);
    root->addChild(offlineBuddy);
    sorter->setRoot(root.get());

    NodePtr n(sorter->gather());
    ASSERT_EQ(1, n->numChildren());
    ASSERT_EQ(L"digsby01", n->children()[0]->data()->name());
}

TEST_F(SorterTest, TestOfflineGrouping)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByGroup(true));
    sorter->addSorter(new ByOnline(true, true));
    sorter->addSorter(new ByMobile(true));

    GroupPtr root(new Group(L"root"));

    Buddy* onlineBuddy = sorter->account(L"digsby01", L"aim")->buddy(L"digsby01");
    Group* buddies = new Group(L"buddies");
    onlineBuddy->setStatus(L"away");
    Buddy* offlineBuddy = sorter->account(L"digsby01", L"aim")->buddy(L"digsby13");
    offlineBuddy->setStatus(L"offline");
    buddies->addChild(onlineBuddy);
    buddies->addChild(offlineBuddy);

    root->addChild(buddies);
    sorter->setRoot(root.get());

    NodePtr n(sorter->gather());
    ASSERT_EQ(2, n->numChildren());
    ASSERT_EQ(L"digsby01", n->children()[0]->children()[0]->data()->name());
    ASSERT_EQ(L"digsby13", n->children()[1]->children()[0]->data()->name());
}

TEST_F(SorterTest, TestPruneEmpty)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());

    sorter->addSorter(new ByGroup(true, 2));
    sorter->addSorter(new ByOnline(false, false));
    sorter->addSorter(new ByMobile(true));
    sorter->setPruneEmpty(true);

    GroupPtr root(new Group(L"none"));
    Group* root0 = new Group(L"Root0");
    Group* contacts = new Group(L"Contacts");

    Buddy* digsby03 = sorter->account(L"digsby01", L"jabber")->buddy(L"digsby03");
    Buddy* digsby04 = sorter->account(L"digsby01", L"jabber")->buddy(L"digsby04");

    root->addChild(root0);
    root0->addChild(contacts);
    contacts->addChild(digsby03);
    contacts->addChild(digsby04);

    sorter->setRoot(root.get());

    NodePtr n(sorter->gather());

    // The Contacts group should be pruned.
    ASSERT_EQ(0, n->numChildren());
}

TEST_F(SorterTest, TestCaseInsensitiveStringCompares)
{
    // Check case insensitive string compares.
    EXPECT_EQ(0, CaseInsensitiveCmp(wstring(L"blah"), wstring(L"Blah")));
    EXPECT_EQ(0, CaseInsensitiveCmp(wstring(L"foo"), wstring(L"foo")));
    EXPECT_EQ(-1, CaseInsensitiveCmp(wstring(L"meep"), wstring(L"meepz")));
    EXPECT_EQ(-1, CaseInsensitiveCmp(wstring(L"meep"), wstring(L"meep baz")));
    EXPECT_EQ(1, CaseInsensitiveCmp(wstring(L"abc"), wstring(L"ABB")));
}

TEST_F(SorterTest, TestToLower)
{
    EXPECT_EQ(L"abc", wstringToLower(L"ABC"));
    EXPECT_EQ(L"abc def", wstringToLower(L"abc def"));
    EXPECT_EQ(L"abc def", wstringToLower(L"AbC dEf"));
}

// For testing GroupByKey
struct GroupByTester
{
    GroupByTester(Node::Vector* vec)
        : v(vec)
    {}

    void callback(const Node::VecIter& i, const Node::VecIter& j)
    {
        starts.push_back(i - v->begin());
        ends.push_back(j - v->begin());
    }

    Node::Vector* v;
    vector<int> starts;
    vector<int> ends;
};

TEST_F(SorterTest, TestGroupByKey)
{
    typedef GroupByKey<Node*> G;
    Node::Vector v;

    // Build a vector of Node*s with keys one, one, one, two, two
    const wchar_t* keys[] = { L"one", L"one", L"one", L"two", L"two" };
    for (int i = 0; i < 5; ++i) {
        Node* n = new Node(NULL, NULL);
        n->setKey(keys[i]);
        v.push_back(n);
    }

    Node::Vector new_v;
    GroupByTester tester(&new_v);
    G g(&new_v, v.size(), boost::bind(&GroupByTester::callback, &tester, _1, _2));
    for (Node::VecIter i = v.begin(); i != v.end(); ++i)
        g.push_back(*i);
    g.finish();

    EXPECT_EQ(2, tester.starts.size());
    EXPECT_EQ(2, tester.ends.size());

    EXPECT_EQ(0, tester.starts[0]);
    EXPECT_EQ(3, tester.ends[0]);

    EXPECT_EQ(3, tester.starts[1]);
    EXPECT_EQ(5, tester.ends[1]);

    for (Node::VecIter i = v.begin(); i != v.end(); ++i)
        delete *i;
}

template <typename T>
void init_vector(vector<T>& v, T* data, int len)
{
    for (int i = 0; i < len; ++i)
        v.push_back(data[i]);
}

TEST_F(SorterTest, TestSortedMerge)
{
    vector<int> a, b, c;

    // three sorted lists:
    int a_[] = { 3, 6, 10, 15 };
    int b_[] = { 1, 20 };
    int c_[] = { 30 };

    init_vector(a, a_, 4);
    init_vector(b, b_, 2);
    init_vector(c, c_, 1);

    vector< vector<int>* > vecs;
    vecs.push_back(&a);
    vecs.push_back(&b);
    vecs.push_back(&c);

    // merge will fill output with all the lists' elements sorted.
    vector<int> output;
    merge(vecs, output, std::greater<int>());

    // assert that output is sorted
    vector<int> outputCopy(output);
    std::sort(outputCopy.begin(), outputCopy.end());
    EXPECT_TRUE(outputCopy == output);
}

TEST_F(SorterTest, TestNthParent)
{
    NodePtr root_ptr(new Node(NULL, NULL));
    Node* root = root_ptr.get();

    NodePtr child_ptr(new Node(NULL, root));
    Node* child = child_ptr.get();

    NodePtr subchild_ptr(new Node(NULL, child));
    Node* subchild = subchild_ptr.get();

    ASSERT_EQ(root,  child->parent());
    ASSERT_EQ(child, child->nthParent(0));
    ASSERT_EQ(root,  child->nthParent(1));
    ASSERT_EQ(child, subchild->parent());
    ASSERT_EQ(root,  subchild->parent()->parent());
    ASSERT_EQ(root,  subchild->nthParent(2));

    ASSERT_EQ(NULL, root->nthParent(1));
    ASSERT_EQ(NULL, root->nthParent(2));
    ASSERT_EQ(NULL, child->nthParent(2));
    ASSERT_EQ(NULL, subchild->nthParent(3));
    ASSERT_EQ(NULL, subchild->nthParent(3000));
}


TEST_F(SorterTest, TestFakeRoot)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByFakeRoot(L"Contacts"));
    sorter->addSorter(new ByGroup(true, 2));
    sorter->addSorter(new ByOnline(true, false));

    GroupPtr root(new Group(L"root"));
    Group* root1 = new Group(L"root1");
    Group* contacts = new Group(L"contacts");
    Group* root2 = new Group(L"root2");
    Group* contacts2 = new Group(L"contacts");

    Buddy* onlineBuddy = sorter->account(L"digsby01", L"aim")->buddy(L"abc");
    Buddy* onlineBuddy2 = sorter->account(L"digsby01", L"aim")->buddy(L"def");
    Buddy* onlineBuddy3 = sorter->account(L"digsby01", L"aim")->buddy(L"ghi");
    Buddy* onlineBuddy4 = sorter->account(L"digsby01", L"aim")->buddy(L"def");

    root1->addChild(contacts);
    root1->addChild(onlineBuddy);
    contacts->addChild(onlineBuddy2);

    root2->addChild(contacts2);
    root2->addChild(onlineBuddy4);
    contacts2->addChild(onlineBuddy3);

    root->addChild(root1);
    root->addChild(root2);

    sorter->setRoot(root.get());

    // Check that the ByFakeRoot grouper does not cause a memory leak.
    NodePtr n(sorter->gather());
    //assert 'contacts' merged with "Contacts"
    ASSERT_EQ(1, n->numChildren());
}

TEST_F(SorterTest, TestOfflineCount)
{
    /*
    fake root group "Contacts"
    real group "Contacts"
    when you group offline contacts, the total number is missing (likely from the fake group)
    */

    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByFakeRoot(L"Contacts"));
    sorter->addSorter(new ByGroup(true, 2));
    sorter->addSorter(new ByOnline(true, true));
    GroupPtr root(new Group(L"root"));
    Group* root1 = new Group(L"root1");
    Group* contacts = new Group(L"contacts");
    Group* root2 = new Group(L"root2");

    Buddy* offlineBuddy = sorter->account(L"digsby01", L"aim")->buddy(L"digsby13");
    offlineBuddy->setStatus(L"offline");
    contacts->addChild(offlineBuddy);

    Buddy* offlineBuddy2 = sorter->account(L"digsby01", L"aim")->buddy(L"digsby2000");
    offlineBuddy->setStatus(L"offline");

    root1->addChild(contacts);

    root2->addChild(offlineBuddy2);

    root->addChild(root1);
    root->addChild(root2);

    sorter->setRoot(root.get()); 
    NodePtr n(sorter->gather()); 
    ASSERT_EQ(2, n->numChildren());

    // the contacts group was merged from a fake root group, and the real
    // contacts group, and should have two "missing" nodes.
    Node* contactsGroup = n->children()[0];
    ASSERT_EQ(L"contacts", contactsGroup->name());
    ASSERT_EQ(2, contactsGroup->missing());

    // both buddies should be in the offline group.
    Node* offlineGroup = n->children()[1];
    ASSERT_EQ(L"Offline", offlineGroup->name());
    ASSERT_EQ(2, offlineGroup->numChildren());
}

TEST_F(SorterTest, TestDuplicateBuddies)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByGroup(true, 2));

    GroupPtr root(new Group(L"root"));
    Group* root1 = new Group(L"root1");
    Group* root2 = new Group(L"root2");

    Buddy* b1 = sorter->account(L"digsby01", L"aim")->buddy(L"foo");
    b1->setStatus(L"away");

    Buddy* b2 = sorter->account(L"digsby03", L"aim")->buddy(L"foo");
    b2->setStatus(L"available");

    root->addChild(root1);
    root->addChild(root2);
    root1->addChild(b1);
    root2->addChild(b2);

    sorter->setRoot(root.get());
    NodePtr n(sorter->gather());

    ASSERT_EQ(1, n->numChildren());
    ASSERT_EQ(L"available", n->children()[0]->data()->asContact()->status());
}

TEST_F(SorterTest, TestBisect)
{
    vector<int> v;
    v.push_back(3);
    v.push_back(6);

    std::less<int> intLess;

    typedef vector<int>::const_iterator Iter;
    Iter begin(v.begin());
    Iter end(v.end());

    ASSERT_TRUE(v.begin()     == bisect_left(v.begin(), v.end(), 3,  &intLess));
    ASSERT_TRUE(v.begin() + 1 == bisect_left(v.begin(), v.end(), 6,  &intLess));
    ASSERT_TRUE(v.end()       == bisect_left(v.begin(), v.end(), 10, &intLess));

    vector<int> v2;
    v2.push_back(10);
    ASSERT_TRUE(v2.begin() == bisect_left(v2.begin(), v2.end(), 10, &intLess));
}

TEST_F(SorterTest, TestMostCapitalized)
{
    vector<wstring> v;
    v.push_back(L"abc"); v.push_back(L"ABC"); v.push_back(L"aBc");

    std::sort(v.begin(), v.end(), MostCapitalizedLess(L"abc"));

    EXPECT_EQ(L"abc", v[0]);
    EXPECT_EQ(L"aBc", v[1]);
    EXPECT_EQ(L"ABC", v[2]);
    EXPECT_EQ(L"ABC", mostCapitalized(L"abc", v));

    v.clear();
    v.push_back(L"ABC"); v.push_back(L"abc"); v.push_back(L"aBc");

    std::sort(v.begin(), v.end(), MostCapitalizedLess(L"abc"));

    EXPECT_EQ(L"abc", v[0]);
    EXPECT_EQ(L"aBc", v[1]);
    EXPECT_EQ(L"ABC", v[2]);
    EXPECT_EQ(L"ABC", mostCapitalized(L"abc", v));

    v.clear();
    v.push_back(L"aBC"); v.push_back(L"abc"); v.push_back(L"Abc");

    std::sort(v.begin(), v.end(), MostCapitalizedLess(L"abc"));

    EXPECT_EQ(L"abc", v[0]);
    EXPECT_EQ(L"Abc", v[1]);
    EXPECT_EQ(L"aBC", v[2]);
    EXPECT_EQ(L"aBC", mostCapitalized(L"abc", v));
}

TEST_F(SorterTest, RemoveAccount)
{
    auto_ptr<Contacts> contacts(new Contacts());
    Account* acct1 = contacts->account(L"digsby01", L"aim");

    EXPECT_EQ(true, acct1->valid());
    ASSERT_TRUE(contacts->removeAccount(L"digsby01", L"aim"));

    //not really removed
    EXPECT_EQ(1, contacts->accounts()->size());
    EXPECT_EQ(false, acct1->valid());

    Account* acct2 = contacts->account(L"digsby01", L"aim");
    EXPECT_EQ(1, contacts->accounts()->size());
    EXPECT_EQ(true, acct2->valid());

    //note: comparing acct2 and acct1 won't work,
    //they may be allocated in the same place.
}

TEST_F(SorterTest, RemoveAccount2)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByFakeRoot(L"Contacts"));
    sorter->addSorter(new ByGroup(true, 2));

    {
        GroupPtr root(new Group(L"root"));
        Group* root1 = new Group(L"root1");
        Group* contacts = new Group(L"contacts");

        Buddy* onlineBuddy = sorter->account(L"digsby01", L"aim")->buddy(L"abc");

        root1->addChild(contacts);
        root1->addChild(onlineBuddy);

        root->addChild(root1);
        
        sorter->setRoot(root.get());

        sorter->removeAccount(L"digsby01", L"aim");
        sorter->clearNodes();
    }

    {
        GroupPtr root2(new Group(L"root"));
        Group* root12 = new Group(L"root1");
        Group* contacts2 = new Group(L"contacts");

        Buddy* onlineBuddy2 = sorter->account(L"digsby01", L"aim")->buddy(L"abc");
        root12->addChild(contacts2);
        root12->addChild(onlineBuddy2);

        root2->addChild(root12);

        sorter->setRoot(root2.get());
        sorter->removeAccount(L"digsby01", L"aim");
        sorter->removeAccount(L"digsby01", L"aim");
        sorter->clearNodes();
    }

    //
    //EXPECT_EQ(0, sorter->accounts()->size());
}


TEST_F(SorterTest, RemoveAccount3)
{

    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByFakeRoot(L"Contacts"));
    sorter->addSorter(new ByGroup(true, 2));
    {
    GroupPtr root(new Group(L"root"));
    Group* root1 = new Group(L"root1");
    Group* contacts = new Group(L"contacts");

    Buddy* onlineBuddy = sorter->account(L"digsby01", L"aim")->buddy(L"abc");
    Contact* contact = onlineBuddy->contact();

    root1->addChild(contacts);
    root1->addChild(onlineBuddy);

    root->addChild(root1);
    
    sorter->setRoot(root.get());

    sorter->removeAccount(L"digsby01", L"aim");
    ASSERT_EQ(0, contact->buddies().size());

    sorter->clearNodes();
    
    }

    
    

}

TEST_F(SorterTest, TestNodeFlags)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByFakeRoot(L"Contacts"));
    sorter->addSorter(new ByGroup(true));
    
    GroupPtr root(new Group(L"root"));
    Group* group = new Group(L"subgroup");
    
    Buddy* b1 = sorter->account(L"digsby01", L"aim")->buddy(L"abc");
    Buddy* b2 = sorter->account(L"digsby01", L"aim")->buddy(L"def");

    root->addChild(b1);
    group->addChild(b2);
    root->addChild(group);

    sorter->setRoot(root.get());

    NodePtr n(sorter->gather());
}

TEST_F(SorterTest, TestNodeFlagStrings)
{
    ASSERT_EQ(L"StatusGroup", stringForNodeFlags(FlagStatusGroup));
    ASSERT_EQ(L"PruneTree | Leaf", stringForNodeFlags(FlagPruneTree | FlagLeaf));
    ASSERT_EQ(L"", stringForNodeFlags(0));
}

TEST_F(SorterTest, TestSearch)
{
    auto_ptr<BuddyListSorter> sorter(new BuddyListSorter());
    sorter->addSorter(new ByGroup(false, 1));
    sorter->addSorter(new BySearch(L"digsby"));

    GroupPtr root(new Group(L"root"));
    Group* group = new Group(L"subgroup");

    Buddy* b1 = sorter->account(L"digsby01", L"aim")->buddy(L"digsby01");
    Buddy* b2 = sorter->account(L"digsby01", L"aim")->buddy(L"digsby02");
    Buddy* b3 = sorter->account(L"digsby01", L"aim")->buddy(L"meep");
    Buddy* b4 = sorter->account(L"digsby01", L"aim")->buddy(L"foop");

    group->addChild(b1);
    group->addChild(b2);
    group->addChild(b3);
    group->addChild(b4);
    root->addChild(group);

    sorter->setRoot(root.get());
    NodePtr n(sorter->gather());

    ASSERT_EQ(1, n->numChildren());
    ASSERT_EQ(2, n->children()[0]->numChildren());
}

