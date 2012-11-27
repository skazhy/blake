#
# blake.core 0.2.0
# Do cool things with your Markdown docs
# skazhy / sept-nov 2012
#

import copy
import os
import re
import unicodedata
import yaml

from datetime import datetime
from markdown import markdown


EXTENSIONS = [".md", ".markdown"]


def _validate_path(path, filename=None, extensions=EXTENSIONS):
    """Checks if given path contains a valid Markdown document."""

    # If no filename is given, assume that it is given in path
    if filename is None:
        path, filename = os.path.split(path)

    name, extension = os.path.splitext(filename)
    extension = extension.lower()

    if not os.path.exists(path):
        return False

    # Ignore hidden files
    if not len(name) or name[0] == '.':
        return False

    #  If given file has a proper extension, return the full path
    for t in extensions:
        if extension == t:
            return os.path.join(path, filename)

    return False


def _relative_subdirectories(src, path):
    """ Gets the relative subdirectory part from 2 given paths."""
    return filter(lambda x: len(x) > 0, path.replace(src, "").split("/"))


def slugify(text, delim='-', escape_html=False):
    """Generates an ASCII-only slug."""

    if type(text) is list:
        text = delim.join(text)

    text = text.decode("UTF-8")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

    _punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

    if escape_html:
        text = re.sub('<[^<]+?>', '', text)

    result = []
    for word in _punct_re.split(text.lower()):
        if word:
            result.append(word)
    return delim.join(result)


class Blake(object):
    @property
    def slug(self):
        """Returns slug of the document."""
        slug = ""
        if "subdirectory" in self.head and self.head["subdirectory"]:
            subdir = self.head["subdirectory"]
            dir_slug = "-".join(map(lambda x: slugify(x), subdir))
            return "-".join([dir_slug, slugify(self.filename)])
        return slugify(self.filename)

    @slug.setter
    def slug(self, value):
        value
        # TODO: implement this

    @property
    def title(self):
        if self._title is not None:
            return self._title
        return self.filename

    @title.setter
    def title(self, value):
        self._title = value


class Document(Blake):
    def __init__(self, filename=None, parse=True, static_prefix=""):
        # Head should be a silent dict-a-like that doesnt keyerror
        self.head = {
            "full_path": filename,
            "subdirectory": []
        }
        self._title = None
        self._content = None
        self.static_prefix = static_prefix

        if parse:
            plaintext_document = self.create()

    def __hash__(self):
        # Unique identifier for 2 newly created docs will work?
        return self.slug.__hash__()

    def __eq__(self, other):
        return hash(self) == hash(other)

    @property
    def filename(self):
        return os.path.splitext(os.path.split(self.head["full_path"])[1])[0]

    @property
    def content(self):
        return markdown(self._content)

    @content.setter
    def content(self, c):
        self._content = c

    def create(self, head=None):
        """Parses the raw document."""
        if self.head["full_path"] is not None:
            plain = open(self.head["full_path"]).read()
            parts = plain.split('---', 2)

            # Format as follows: ["", "yaml front matter", "markdown"]
            if not parts[0]:
                yaml_present = True

            if yaml_present:
                head = yaml.load(parts[1])
                if "title" in head:
                    self.title = head["title"]
                    head.pop("title")
                # TODO: A custom iterable type for these would be nice
                if "tags" in head:
                    tag_list = head["tags"].split(",")
                    self.head['tags'] = map(lambda t: t.strip(), tag_list)
                    head.pop("tags")
                for key in head:
                    self.head[key] = head[key]
                self.content = parts[2].decode("UTF-8")
            else:
                self.content = plain.decode("UTF-8")

            # TODO: move image handling section to a seperate method, as
            #       rendering will happen on the fly and there is no need to
            #       do this in advance
            self.images = map(lambda i: i, re.findall('!\[.*\]\((.*)\)', plain))

            for img in self.images:
                # TODO: Move external image *identifiers* to a custom property
                if img[:7] != "http://" and img[:8] != "https://" and img[:2] != "//":
                    self.content = self.content.replace(img, self.static_prefix + img)

        # Extra params in head argument override those found in yaml (if any)
        if head is not None:
            for key in head:
                self.head[key] = head[key]

        if "published" in self.head:
            try:
                self.head['published'].now()
            except AttributeError:
                self.head['published'] = datetime.now()

    def to_dict(self, include=[], exclude=[]):
        """ Return a dict representing attributes. """
        d = {}
        if exclude is None:
            exclude = []
        for key in self.head.keys():
            if key not in exclude:
                d[key] = self.head[key]

        d["slug"] = self.slug
        d["filename"] = self.filename
        d["title"] = self.title

        if "category" in d:
            d["category_slug"] = slugify(self.head["category"])

        if self.content is not None:
            d["content"] = self.content

        # If include is present - leave only given keys
        # This is kinda dangerous -as is-
        if include:
            for key in d.keys():
                if key not in include:
                    d.pop(key)

        if "subdirectory" in d:
            d["subdirectory"] = "/".join(self.head["subdirectory"])

        return d

    def slugify(self, attr):
        """ Slugify a head attr."""
        if attr in self.head:
            return slugify(self.head[attr])
        return None

    def add_slug(self, *args, **kwargs):
        for arg in args:
            if arg in self.head:
                self.head["%s_slug" % arg] = slugify(self.head[arg])


def create_document(src, static_prefix=""):
    doc_path = _validate_path(src)
    if doc_path:
        return Document(src, static_prefix=static_prefix)
    return False


class DocumentList(Blake):
    def __init__(self, src=None, static_prefix="", recursive=True):
        self._documents = []
        self.document = Document
        self.static_prefix = static_prefix
        self.subdirectory = []

        if src:
            load(src, recursive=recursive)

    # TODO: if stop is a slice return inheritance-safe DocList, not an array.
    def __getitem__(self, stop):
        return self._documents[stop]

    def __iter__(self):
        for doc in self._documents:
            yield doc

    def __len__(self):
        return len(self._documents)

    # documentlist += document
    def __iadd__(self, doc):
        if isinstance(doc, Document):
            self._documents.append(doc)

    @property
    def documents(self):
        return self._documents

    @documents.setter
    def documents(self, docs):
        self._documents = docs

    def add(self, filename=None, parse=True, static_prefix=""):
        # TODO: nested documentlists
        doc = self.document(filename=filename, parse=parse, static_prefix=static_prefix)
        self += doc

    def load(self, src, recursive=True):
        valid_documents(src, instance=self, recursive=recursive)

    # When adding the custom iterable type, should extend this to support
    # eg  list.find(tags__contain="one tag")
    # TODO: currently this is will raise errors when querying for head
    #       properties not present in all docs. the silent dict should fix this
    def find(self, *args, **kwargs):
        """ Query the documentlist. Return a DL with fewer results."""
        if kwargs:
            a = copy.copy(self)
            while kwargs:
                key, value = kwargs.popitem()
                if key == "title":
                    a.documents = filter(lambda x: x.title == value, a)
                elif key == "filename":
                    a.documents = filter(lambda x: x.filename == value, a)
                elif key == "slug":
                    a.documents = filter(lambda x: x.slug == value, a)
                else:
                    a.documents = filter(lambda x: x.head[key] == value, a)
            return a
        return self

    def to_list(self, include=[], exclude=[]):
        return map(lambda d: d.to_dict(include=include, exclude=exclude), self)

    def get(self, *args, **kwargs):
        """ Retrieve a single document. """
        doc = self.find(*args, **kwargs).documents
        if not len(doc):
            return None
        return doc[0]

    def distinct(self, key):
        """ Get distinct values of an attribute. """
        values = []
        if key == "title":
            for doc in self:
                values.append(doc.title)
        elif key == "filename":
            for doc in self:
                values.append(doc.filename)
        elif key == "slug":
            for doc in self:
                values.append(doc.slug)
        else:
            for doc in self:
                if key in doc.head:
                    values.append(doc.head[key])
        return set(values)

    def to_list(self, include=[], exclude=[]):
        """ Returns list of to_dict for each of the elements. """
        return map(lambda d: d.to_dict(include=include, exclude=exclude), self)


def valid_documents(src, parse=True, instance=None, static_prefix="", recursive=True):
    # This allows to populate the DL from customized instances
    if instance is not None:
        d = instance
    else:
        d = DocumentList()

    if recursive:
        for (path, dirs, files) in os.walk(src):
            for filename in files:
                doc_path = _validate_path(path, filename)
                if doc_path:
                    d.add(filename=doc_path, parse=parse, static_prefix=static_prefix)
                    d[-1].head["subdirectory"] = _relative_subdirectories(src, path)
    else:
        for filename in os.listdir(src):
            doc_path = _validate_path(src, filename)
            if doc_path:
                d.add(doc_path, parse, static_prefix=static_prefix)
    if instance is not None:
        return True
    return d
