#ifndef SortBy_h
#define SortBy_h
/**
 * Attributes which we sort and group by.
 *
 * For now, this enum must be duplicated in sip/blist.sip
 */

enum SortBy
{
    UserOrdering = 1,
    Name         = 2,
	LogSize      = 4,
	Service      = 8, 
	Status       = 16,
    Alias        = 32,
    CustomOrder  = 64,
    Mobile       = 128,
    Online       = 256,
};

const SortBy AllSearchable = static_cast<SortBy>(Name | Alias);

const SortBy sortBys[] =
    {UserOrdering, Name, LogSize, Service, Status, Alias, CustomOrder, Mobile, static_cast<SortBy>(0)};

#endif //SortBy_h
