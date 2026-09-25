// Bomb.cpp: implementation of the Bomb class.
//
//////////////////////////////////////////////////////////////////////

#include "stdafx.h"
#include "B.h"
#include "Bomb.h"

#ifdef _DEBUG
#undef THIS_FILE
static char THIS_FILE[]=__FILE__;
#define new DEBUG_NEW
#endif

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////
Bomb::Bomb(bool pl,int x,int y,bool b)
{
	cpxy.x=x;
	cpxy.y=y;
	active=b;
	player1=pl;
	savekadr=kadr=0;
	bb[0]=bb[1]=bb[2]=bb[3]=true;
	temp=0;
	for(int i=0;i<9;i++)
			bumb[i].x=-100;
}



bool Bomb::NextStep()
{
	savekadr=kadr;
	if (kadr<4)
	{
		if (temp==3) 
		{
			kadr++;
			temp=0;
		}
		else temp++;

	}
	else kadr++;
	
	if (kadr>18) 
	{
		kadr=0;
		active=false;
		return true;// Бомба взорвалась
	}
	return false;
}
