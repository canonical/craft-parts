#include <stdio.h>

// "Stringify" macros to turns the preprocessor constants GREETING and PERSON_NAME
// into strings to print
#define xstr(s) str(s)
#define str(s) #s

int main()
{
    printf("%s, %s!\n", xstr(GREETING), xstr(PERSON_NAME));
    return 0;
}
