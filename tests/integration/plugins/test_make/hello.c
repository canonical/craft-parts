#include <stdio.h>

// Compile-time configurable message
#ifndef MESSAGE
#define MESSAGE "Hello"
#endif

#ifndef TARGET
#define TARGET "world"
#endif

int main()
{
    printf("%s, %s!\n", MESSAGE, TARGET);
    return 0;
}
