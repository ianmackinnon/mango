### Test static

Will destroy database contents!

Shell 1:

    make test
    
Shell 2:

    ./test/test_web.py -v
    
Debugging:

    chromium-browser /tmp/mango-error.html
    
Check malicous markdown (with and without JS)
    
    http://localhost:8802/organisation/1
    
    
### Test versioning

Shell:

    make test

Browser main

    http://localhost:8802/auth/login/local?user=1
    
Browser incognito

    http://localhost:8802/auth/login/local?user=3
    
-   companies
-   edit
-   create
-   make a company (id: 2)
-   attach contact to org
-   attach address to org

Browser main

-   edit
-   queue
-   accept all (public)

Browser incognito

    http://localhost:8802/organisation/2?view=edit    

-   edit company
-   edit contact
-   edit address

Browser main

-   edit
-   queue
-   decline all (public)

Now repeat for events
