# $Id: pstests.py,v 1.1 2000/10/28 22:33:56 clee Exp $
import pidtest

def testLatin1Chars(can):
    curx,cury = 10,20
    can.drawString("hola Málaga amigos niños", curx,cury)
    cury = cury + 20
    can.drawString("Como estan?", curx, cury)

    can.flush()
    can.clear()  # get our next page ???
    curx,cury = 10,20
    can.drawString("hola Málaga amigos niños: Page 2", curx,cury)

    str = "sometextÄËÖ with ácënts"
    print len("ÄËÖ")
    pidtest.CenterAndBox(can, str, y=150)

    can.flush()


