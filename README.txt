=====
Blake
=====

Do all sorts of cool things with your Markdown documents. Use it for
displaying static content in your Python webapp, backup documents in a
database (currently  - only MongoDB) or create your custom Jekyll spinoff 
(Blake has full support for legit Jekyll posts).

This is a (very) early development verion. Things could crash, burn and make
you listen Cher all night, if used the wrong way.

Syncing data between MongoDB & your Markdown folder is as easy as:    
    
    #! /usr/bin/env python

    from blake.mongodb import MongoDocumentList

    docs = MongoDocumentList()

    docs.load('/path/to/markdown/files/')
   
    docs.save()
