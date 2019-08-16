import json


def savejson(filename, struct):
    try:
        for key in struct["sources"]:
            tmp = struct["sources"][key]
            newkey = str(hash(json.dumps(tmp)))
            del struct["sources"][key]
            struct["sources"][newkey] = tmp
    except:
        pass
    with open(filename, "w") as fd:
        fd.write(json.dumps(struct, indent=4, sort_keys=True))


def openjson(filename):
    with open(filename, "r") as fd:
        t = fd.read()
        s = json.loads(t)
        if len(s) <= 0:
            return {}
        return s


def ppjson(inputs):
    """
    Pretty prints inputs which are assumed json filename, text, or structure.
    """
    try:
        with open(inputs, "r") as fd:
            print(json.dumps(json.loads(fd.read()), indent=4, sort_keys=True))
    except:
        try:
            print(json.dumps(json.loads(inputs), indent=4, sort_keys=True))
        except:
            print(json.dumps(inputs, indent=4, sort_keys=True))


def addSource(
    filename, type, name, prefix, postfix, x, y, zoom, notes="", ext="png", DEBUG=False
):
    try:
        struct = openjson(filename)
    except:
        if DEBUG:
            print("unable to save json contents")
        return False
    new = {}
    new["type"] = str(type)
    new["name"] = str(name)
    new["prefix"] = str(prefix)
    new["postfix"] = str(postfix)
    new["x"] = str(x)
    new["y"] = str(y)
    new["zoom"] = str(zoom)
    new["ext"] = str(ext)
    new["notes"] = str(notes)
    uid = str(hash(json.dumps(new)))
    try:
        len(struct["sources"])
    except:
        struct["sources"] = {}
    struct["sources"][uid] = new
    try:
        savejson(filename, struct)
    except:
        if DEBUG:
            print("unable to save json contents")
        return False
    return True


def searchSource(filename, search={}, DEBUG=False):
    try:
        struct = openjson(filename)
    except:
        struct = {"sources": {}}
    output = {"sources": {}}
    if DEBUG:
        print(json.dumps(struct, indent=4, sort_keys=True))
    if DEBUG:
        print(list(search.keys()))
    for uid in list(struct["sources"].keys()):
        for attrib in list(search.keys()):
            try:
                val = struct["sources"][uid][attrib]
                test = val.find(search[attrib]) >= 0
                if DEBUG:
                    print([uid, attrib, val, search[attrib], test])
                if test:
                    output["sources"][uid] = struct["sources"][uid]
            except:
                pass
    return output["sources"]


def rmSource(filename, uid):
    try:
        struct = openjson(filename)
        del struct["sources"][uid]
        savejson(filename, struct)
    except:
        return False
    return True


def main():
    print("-- Insert Test Source")
    fname = "sources.json"
    addSource(
        fname,
        "Satellite",
        "Test Source",
        "www.google.com/",
        "&fetch=True",
        "&x=",
        "&y=",
        "&z=",
    )
    ppjson(fname)
    print("-- Search For Test Source")
    found = searchSource(fname, search={"name": "ource"})
    ppjson(found)
    print("-- Remove Test Source")
    for key in list(found.keys()):
        print("--- Removing: ", key, rmSource(fname, key))
    ppjson(fname)


if __name__ == "__main__":
    main()
