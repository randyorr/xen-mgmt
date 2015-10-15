#!/usr/bin/env python

import redis
from xenClient import Client

def main():

    r = redis.StrictRedis(host='localhost', port=6379, db=0)
    c = Client()
    vm_list = c.list()
    members = set([x.get('name') for x in vm_list])
    response = r.sadd('all', *members)
    print response
    for x in vm_list:
        response = r.hmset(x.get('name'), x)
        print response

if __name__ == "__main__":
    main()
