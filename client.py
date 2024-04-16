def send():
    sendto(pickle.dumps({"playerpos":(x,y), "changes":[[col, row], [col, row]], "newvalues":[newval, newval]})