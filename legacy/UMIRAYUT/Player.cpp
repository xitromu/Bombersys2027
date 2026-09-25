// Player.cpp: implementation of the Player class.
//
//////////////////////////////////////////////////////////////////////

#include "stdafx.h"
#include "Player.h"
#include "Bonus.h"

#ifdef _DEBUG
#undef THIS_FILE
static char THIS_FILE[]=__FILE__;
#define new DEBUG_NEW
#endif

//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////

Player::Player(bool bb,CString name,CString files,UINT a1,UINT a2,UINT a3,UINT a4,UINT a5,int i1,int j1,bool a)
{
	::SetCurrentDirectory("C:/BOMBERSYS/");	
	move=savemove=stop;
	kadr=4;
	player1=bb;
	timetrupx=0;
	timetrupy=0;
	stoptrup=false;
	l=a1;
	r=a2;
	t=a3;
	b=a4;
	bum=a5;
	active=a;
	if (a) n_live=5;
	else n_live=0;
	n_bomb=3;
	score=0;
	cpxy.x=i1*49;
	cpxy.y=j1*49;
	savecpxy=cpxy;
	//| »ћя √≈–ќя
	if (name!="") nameplayer=name;
	else 
	{
		if (bb) nameplayer="»ван";
		else nameplayer=" ол€н";
	}
	if (player1)
		kadr=13;
	else
		kadr=0;

	
	//////////////////////////////////////////////////////////////////
	//| »«ќЅ–ј∆≈Ќ»я √≈–ќя |
	HINSTANCE hInst = AfxGetInstanceHandle();// ƒл€ буфера
	int i=0;
	CString namefile;
	
	i=files.Find(" ");
	namefile=files.Left(i);
	files=files.Right(files.GetLength()-i-1);
	facebmp   = (HBITMAP)::LoadImage(hInst,namefile, IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	
	i=files.Find(" ");
	namefile=files.Left(i);
	files=files.Right(files.GetLength()-i-1);
	playerbmp = (HBITMAP)::LoadImage(hInst,namefile, IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	
	i=files.Find(" ");
	namefile=files.Left(i);
	files=files.Right(files.GetLength()-i-1);
	trupbmp   = (HBITMAP)::LoadImage(hInst,namefile, IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	
	i=files.Find(" ");
	namefile=files.Left(i);
	files=files.Right(files.GetLength()-i-1);
	strupbmp   = (HBITMAP)::LoadImage(hInst,namefile, IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);

	plusbmp = (HBITMAP)::LoadImage(hInst,files, IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
}

void Player::FindBonus(Sort sort)
{
	int savescore=score;
	switch (sort)	
	{
		case door:
		{
			active=false;
			break;
		}
		case sunduk:
		{	
			score+=1000;
			break;
		}
		case bomba:
		{
			if (n_bomb<5) n_bomb++;
			else score+=100;
			break;
		}
		case live:
		{
			n_live++;
			break;
		}
		case smert:
		{
	
			if ((kadr>=0)&&(kadr<=6))	// влево развЄрнут-влево упадЄт			
			{
				move=ltrup;
				kadr=0;
			}
			if ((kadr>=7)&&(kadr<=13))	// вправо раззвЄрнут-вправо упадЄт	
			{
				move=rtrup;
				kadr=29;
			}
			if ((kadr>=14)&&(kadr<=20))	// вверх ... 
			{
				move=ttrup;
				kadr=30;
			}
			if ((kadr>=21)&&(kadr<=27))	// вниз...
			{
				move=btrup;
				kadr=44;
			}
			if (n_live>0) n_live--;
			break;
		}
		case meshok:
		{
			score+=100;
			break;
		}
		case bigmeshok:
		{
			score+=200;
			break;
		}
		case bruliki:
		{
			score+=500;
			break;
		}
		case nasledstvo:
		{
			score+=1000;
			break;
		}
	}//end switch
	if ((savescore/5000)!=(score/5000)) n_live++;

}
void Player::NextStep(char **Matrix,Bonus *bonus[10])
{
	char SXY[12]={0,0,5,19,27,32,37,43,43,43,43,43};// ƒл€ влево-вправо при суперсмерти
	char STXY[12]={0,5,7,7,20,20,20,20,20,20,20,20};
	char trupdx=0,trupdy=0;


	if (move==sltrup) cpxy.x+=SXY[timetrupx];
	if (move==srtrup) cpxy.x-=SXY[timetrupx];
	if (move==sttrup) cpxy.y+=STXY[timetrupy];
	if (move==sbtrup) cpxy.y-=SXY[timetrupy];

	char i=char(cpxy.x/49);
	char j=char(cpxy.y/49);
	char dx=char((cpxy.x-i*49)/7);
	char dy=char((cpxy.y-j*49)/7);
	
	bool bonustrup=false;
	switch (move)	
	{
		///// "ѕ≈–≈ћ≈ў≈Ќ»≈ √≈–ќя"
		case left:
		{
			int jj=j;
			if ((dy==0)||(dy==1)||(dy==5)||(dy==6))
			{				
				if (dx==0)
				{	
					if (dy>4) jj++;
					if ((i>0)&&(Matrix[jj][i-1]<50))
					{
							if (dy>4) j++;
							dy=0;
							i--;
							dx=6;
					}
					kadr=0;
					break;
				}
				else
				{	
					dx--;	
					kadr=6-dx;		
				}
			}
			else kadr=0;
			break;
		}
		case right:
		{
			int jj=j;
			if ((dy==0)||(dy==1)||(dy==5)||(dy==6)) // "—глаженный" поворот
			{	
				if (dx==0)
				{
					if (dy>4) jj++;
					if ((i<14)&&(Matrix[jj][i+1]<50))
					{
							if (dy>4) j++;
							dy=0;
							dx=1;
							kadr=7;
					}
					else 
						kadr=13;
					break;
				}
				else
				{
					dx++;
					kadr=6+dx;	
					if (dx==7) 
					{
						dx=0;
						kadr=13;
						i++;
					}
				}
			}
			else kadr=13;
			break;
		}
		case top:
		{		
			int ii=i;
			if ((dx==0)||(dx==1)||(dx==6)) // "—глаженный" поворот
			{
				if (dy==0)
				{
					if (dx==6) ii++;
					if ((j>0)&&(Matrix[j-1][ii]<50))
					{
							if (dx==6) i++;
							dx=0;
							j--;
							kadr=15;
							dy=6;
					}
					else kadr=14;
					break;
				}	
				else 
				{
					dy--;
					kadr=14+dy;
				}
			}
			else kadr=14;
			break;
		}
		case bottom:
		{
			int ii=i;
			if ((dx==0)||(dx==1)||(dx==6)) // "—глаженный" поворот
			{
				if (dy==0)
				{
					if (dx==6) ii++;
					if ((j<14)&&(Matrix[j+1][ii]<50))
					{
							if (dx==6) i++;
							dx=0;
							kadr=22;
							dy++;
					}
					else kadr=21;
					break;
				}
				else 
				{
					dy++;
					kadr=21+dy;
					if (dy==7) 
					{
						dy=0;
						kadr=21;
						j++;
					}
				}
			}
			else kadr=21;
			break;
		}

		///// "—ћ≈–“№"	
		case ltrup:  // кадры:(0-14)
		{		
			if (kadr<14) 
			{
				kadr++;
				timetrupx++;	
				if (kadr==14) 
					trupdy=7;
			}
			else bonustrup=true;
			 //ѕоправки
			if (kadr==8)  trupdx=-13;
			if (kadr==9)  trupdx=-7;
			break;
		}
		case rtrup: // кадры:(15-30)
		{		
			if (kadr>15) 
			{
				kadr--;
				timetrupx++;
				if (kadr==15) 
					trupdy=7;
			}
			else bonustrup=true;
			// ѕоправки
			if (kadr==20)  trupdx=7;
			if (kadr==21)  trupdx=13;
			
			break;
		}	
		
		case ttrup:// кадры:(31-43)
		{
			if (kadr<43) 
			{
				kadr++;
				timetrupx++;
			}
			else bonustrup=true;
		
			break;
		}		
		case btrup:// кадры:(44-58)
		{		
			if (kadr<57) 
			{
				kadr++;
				timetrupx++;
			}
			else bonustrup=true;
			// ѕоправки
			if ((kadr==50)&&(cpxy.y<671)) trupdy=15;
			if (kadr==52) trupdy=7;
			break;
		}
		///// "Ё — Ћё«»¬Ќјя —ћ≈–“№"
		case srtrup: // кадры:(0-10)
		{		
			if (kadr<10) 
			{
				kadr++;
				timetrupx++;
			}
			else bonustrup=true;
			break;
		}		
		case sltrup:  // кадры:(11-21)
		{		
			if (kadr>11) 
			{
				kadr--;
				timetrupx++;
			}
			else bonustrup=true;
			break;
		}
		case sbtrup:// кадры:(22-32)
		{
			if (kadr<32) 
			{
				kadr++;
				timetrupy++;
			}
			else bonustrup=true;
			break;
		}
		case sttrup:// кадры:(33-43)
		{		
			if (kadr<43) 
			{
				kadr++;
				timetrupy++;
			}
			else bonustrup=true;
			break;
		}

	}// end switch	

	cpxy.x=i*49+7*dx;
	cpxy.y=j*49+7*dy;	
	if (bonustrup)
	{
		if ((bonus[9]->on_off)&&(!bonus[9]->active))
		{
			bonus[9]->active=true;
			bonus[9]->cpxy.x=cpxy.x;
			bonus[9]->cpxy.y=cpxy.y;
		}
		n_bomb=3;
		stoptrup=true;
	}
	if (move==sltrup) cpxy.x-=SXY[timetrupx];
	if (move==srtrup) cpxy.x+=SXY[timetrupx];
	if (move==sttrup) cpxy.y-=STXY[timetrupy];
	if (move==sbtrup) cpxy.y+=SXY[timetrupy];
	if ((move<sltrup)&&(move>stop))
	{
		cpxy.x+=trupdx;
		cpxy.y+=trupdy;
	}
	//////////////////////////////////////////////////////////////
	// √ерой попадает на взрыв, бонус или врага.
	
	for(int k=0;k<10;k++)	//ѕрорисовка размещЄнных, но не собранных бонусов
	{
		if ((bonus[k]->active)&&(bonus[k]->on_off))
		{

			int kk=((cpxy.x-bonus[k]->cpxy.x)*(cpxy.x-bonus[k]->cpxy.x)+(cpxy.y-bonus[k]->cpxy.y)*(cpxy.y-bonus[k]->cpxy.y));			
			if ((kk<525)&&(move<ltrup))
			{
				if (bonus[k]->sort!=door) bonus[k]->on_off=false;
				FindBonus(bonus[k]->sort);
			}
		}
	}
	bool bu=false;
	if ((dx>1)&&(dx<5)) 
	{
		if ((Matrix[j][i+1]>10)&&(Matrix[j][i+1]<20)) bu=true;
	}
	if ((dy>1)&&(dy<5)) 
	{
		if ((Matrix[j+1][i]>10)&&(Matrix[j+1][i]<20)) bu=true;
	}
	// ѕопал на взрыв
	if (((Matrix[j][i]>10)&&(Matrix[j][i]<20)||(bu))&&(move<ltrup))
	{
			if (dx>3) i++;
			if (dy>3) j++;
			timetrupx=0;
			timetrupy=0;
			if ((kadr>=0)&&(kadr<=6))	// влево развЄрнут-влево упадЄт			
			{
				move=ltrup;
				kadr=0;
				if ((i<13)&&(Matrix[j][i+1]<50)&&(Matrix[j][i+1]>10)&&(Matrix[j][i+1]<20)&&(Matrix[j][i+2]==10))
				{
						move=srtrup;
						kadr=0;
						return;
				}
			}
			if ((kadr>=7)&&(kadr<=13))	// вправо раззвЄрнут-вправо упадЄт	
			{
				move=rtrup;
				kadr=29;
				i++;
				if ((i>=2)&&(Matrix[j][i-1]<50)&&(Matrix[j][i-1]>10)&&(Matrix[j][i-1]<20)&&(Matrix[j][i-2]==10))
			
				{
						move=sltrup;
						kadr=21;
						return;
				}
			}
			if ((kadr>=14)&&(kadr<=20))	// вверх ... 
			{
				move=ttrup;
				kadr=30;
				if ((j<13)&&(Matrix[j+1][i]<50)&&(Matrix[j+1][i]>10)&&(Matrix[j+1][i]<20)&&(Matrix[j+2][i]==10))
				{
						move=sbtrup;
						kadr=22;
						return;
				
				}
			}
			if ((kadr>=21)&&(kadr<=27))	// вниз...
			{
				move=btrup;
				kadr=44;
				j++;
				if ((j>=2)&&(Matrix[j-1][i]<50)&&(Matrix[j-1][i]>10)&&(Matrix[j-1][i]<20)&&(Matrix[j-2][i]==10))
				{
						move=sttrup;
						kadr=32;
						return;
				}
			}
		if (n_live>0) n_live--;
			
	}
//////////////////////////////////////////////////////////////
}

