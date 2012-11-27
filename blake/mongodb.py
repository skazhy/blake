#
# blake.mongodb 0.2.0
# Do cool things with your Markdown docs and MongoDB
# skazhy / sept-nov 2012
#

from core import Document, DocumentList
import pymongo


class MongoDocument(Document):
    def save(self, db, exclude=[]):
        # Add an option to set a custom primary key field, perhaps?
        db.update({"slug": self.slug},
                  {"$set": self.to_dict(exclude=exclude)}, upsert=True)


class MongoDocumentList(DocumentList):
    def __init__(self, *args, **kwargs):
        super(MongoDocumentList, self).__init__(*args, **kwargs)
        self.document = MongoDocument

    def save(self, db, sync=True, fields=None, exclude=[]):
        if sync:
            # TODO: should allow more control over upserting process
            new_slugs = map(lambda doc: doc.to_dict(exclude=exclude), self)
            for doc in db.find({}):
                if doc['slug'] not in new_slugs:
                    db.remove(doc)

        for doc in self:
            doc.save(db, fields)
        return self
