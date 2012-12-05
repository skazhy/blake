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


class QueryDict(object):
    def __init__(self, d=None):
        if d is not None:
            self._dict = d
        else:
            self._dict = {}

    def __getitem__(self, key):
        return self._dict.get(key, None)

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __delitem__(self, key):
        if key in self._dict:
            self._dict.pop(key)

    def __iter__(self):
        for key in self._dict:
            yield key

    def keys(self):
        return self._dict.keys()


class AttrList(object):
    # TODO: blake0.2.2 should add more functions to both of these
    #       classes
    def __init__(self):
        self._list = []

    def __getitem__(self, key):
        return self._list[key]

    def __setitem__(self, key, value):
        self._list[key] = value

    def __iter__(self):
        for item in self._list:
            yield item

    def __str__(self):
        return ",".join(self._list)

    def __unicode__(self):
        return ",".join(self._list)

    def append(self, item):
        self._list.append(item)


def islocal(path):
    if path[:7] == "http://" or path[:8] == "https://" or path[:2] == "//":
        return False
    return True


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
    text = unicodedata.normalize("NFKD", text)  # transform to normalforms
    text = text.encode("ascii", "ignore").decode("ascii")

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
        if self._slug is not None:
            return self._slug
        slug = ""
        if "subdirectory" in self.head and self.head["subdirectory"]:
            subdir = self.head["subdirectory"]
            dir_slug = "-".join(map(lambda x: slugify(x), subdir))
            return "-".join([dir_slug, slugify(self.filename)])
        if self.filename is not None:
            return self.filename
        return None

    @slug.setter
    def slug(self, value):
        self._slug = slugify(value)

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
        self.head = QueryDict({
            "full_path": filename,
            "subdirectory": []
        })
        self._slug = None
        self._title = None
        self._content = ""
        self.static_prefix = static_prefix

        if parse:
            self.create()

    def __hash__(self):
        # Unique identifier for 2 newly created docs will work?
        return self.slug.__hash__()

    def __eq__(self, other):
        return hash(self) == hash(other)

    @property
    def filename(self):
        if self.head["full_path"] is not None:
            path, filename = os.path.split(self.head["full_path"])
            filename, extension = os.path.splitext(filename)
            return filename
        return None

    @property
    def images(self):
        return map(lambda i: i, re.findall('!\[.*\]\((.*)\)', self._content))

    @property
    def content(self):
        md = markdown(self._content)
        for img in filter(lambda x: islocal(x), self.images):
            md = md.replace(img, self.static_prefix + img)
        return md

    @content.setter
    def content(self, c):
        self._content = c

    def create(self, head=None):
        """Parses the raw document."""
        if self.head["full_path"] is not None:
            blakefile = open(self.head["full_path"], "r")
            cont = ""
            yaml_present = False
            blakefile.readline()   # This line should always contain "---"
            line = blakefile.readline()
            while line:
                if line[0] == "-":
                    yaml_present = True
                    break
                cont += line
                line = blakefile.readline()

            if yaml_present:
                # The following line is the bottleneck of #create(), should
                # investigate how to boost YAML parsing
                h = yaml.load(cont)
                for key in h:
                    if key == "title":
                        self._title = h["title"]
                    elif key == "tags":
                        self.head["tags"] = AttrList()
                        [self.head["tags"].append(t.strip()) for t in h["tags"].split(",")]
                    else:
                        self.head[key] = h[key]
                line = blakefile.readline()
                while line:
                    self._content += line
                    line = blakefile.readline()
            else:
                self._content = cont
            blakefile.close()
            self._content = self._content.decode("UTF-8")

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
                d[key] = self.head[key].__str__()

        if "slug" not in exclude:
            d["slug"] = self.slug
        if "filename" not in exclude:
            d["filename"] = self.filename
        if "title" not in exclude:
            d["title"] = self.title
        if "content" not in exclude:
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

    def dump(self):
        yield "---"
        exc = ["full_path", "subdirectory", "content", "filename", "slug"]
        dct = self.to_dict(exclude=exc)
        for key in dct:
            yield "%s: %s" % (key, dct[key])
        yield "---"
        yield self._content


class DocumentList(Blake):
    document = Document

    def __init__(self, src=None, static_prefix="", recursive=True):
        self._documents = []
        self._slug = None
        self.static_prefix = static_prefix
        self.subdirectory = []

        if src:
            self.add(src, recursive=recursive)

    def __getitem__(self, i):
        if isinstance(i, slice):
            a = copy.copy(self)
            a._documents = self._documents[i]
            return a
        else:
            return self._documents[i]

    def __iter__(self):
        for doc in self._documents:
            yield doc

    def __len__(self):
        return len(self._documents)

    # documentlist += document
    def __iadd__(self, doc):
        if isinstance(doc, Document):
            self._documents.append(doc)
        return self

    @property
    def documents(self):
        return self._documents

    @documents.setter
    def documents(self, docs):
        self._documents = docs

    def add(self, filename=None, parse=True, static_prefix="", recursive=True):
        # TODO: nested documentlists
        if not os.path.exists(filename):
            return False
        if os.path.isdir(filename):
            valid_documents(filename, parse=parse,
                            instance=self,
                            static_prefix=static_prefix,
                            recursive=recursive)
        else:
            self += self.document(filename=filename,
                                  parse=parse,
                                  static_prefix=static_prefix)
        return True

    # When adding the custom iterable type, should extend this to support
    # eg  list.find(tags__contain="one tag")
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

    def distinct(self, key, sparse=True):
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
                values.append(doc.head[key])
        s = set(values)
        if sparse and None in s:
            s.remove(None)
        return s

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
