// Bonus.cpp: implementation of the Bonus class.
//
//////////////////////////////////////////////////////////////////////

#include "stdafx.h"
#include "B.h"
#include "Bonus.h"

#ifdef _DEBUG
#undef THIS_FILE
static char THIS_FILE[]=__FILE__;
#define new DEBUG_NEW
#endif

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////




//enum Sort {door,sunduk,bomba,live,smert,meshok,bigmeshok,bruliki,nasledstvo};
Bonus::Bonus(Sort s)
{
	cpxy.x=0;cpxy.y=0;
	on_off=true;
	active=false;
	sort=s;
	ReplaceBmp();
}

Bonus::~Bonus()
{

}

void Bonus::ReplaceBmp()
{
	HINSTANCE hInst = AfxGetInstanceHandle();// Для буфера
	CString bonusfile;
	switch (sort)	
	{
		case door:
		{
			bonusfile="door.bmp";
			break;
		}
		case sunduk:
		{
			bonusfile="sunduk.bmp";
			break;
		}
		case bomba:
		{
			bonusfile="bomba.bmp";
			break;
		}
		case live:
		{
			bonusfile="live.bmp";
			break;
		}
		case smert:
		{
			bonusfile="smert.bmp";
			break;
		}
		case meshok:
		{
			bonusfile="meshok.bmp";
			break;
		}
		case bigmeshok:
		{
			bonusfile="bigmeshok.bmp";
			break;
		}
		case bruliki:
		{
			bonusfile="bruliki.bmp";
			break;
		}
		case nasledstvo:
		{
			bonusfile="nasledstvo.bmp";
			break;
		}
	}//end switch
	bonusbmp   = (HBITMAP)::LoadImage(hInst,bonusfile, IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
}
