import random
def genotp():
    otp=''
    u_l=[chr(i) for i in range(ord('A'),ord('Z')+1)]
    s_l=[chr(i) for i in range(ord('a'),ord('z')+1)]
    n=[i for i in range(0,10)]
    for i in range(2):
        otp+=random.choice(u_l)+str(random.choice(n))+random.choice(s_l)
    return otp