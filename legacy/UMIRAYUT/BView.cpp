// BView.cpp : implementation of the BView class
//

#include "stdafx.h"
#include "B.h"
#include "Bomb.h"
#include "Game.h"
#include "Player.h"
#include "BDoc.h"
#include "BView.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#undef THIS_FILE
static char THIS_FILE[] = __FILE__;
#endif

/////////////////////////////////////////////////////////////////////////////
// BView

IMPLEMENT_DYNCREATE(BView, CView)

BEGIN_MESSAGE_MAP(BView, CView)
	//{{AFX_MSG_MAP(BView)
	ON_WM_ERASEBKGND()
	ON_WM_CREATE()
	ON_WM_KEYDOWN()
	ON_WM_TIMER()
	ON_WM_KEYUP()
	//}}AFX_MSG_MAP
END_MESSAGE_MAP()

/////////////////////////////////////////////////////////////////////////////
// BView construction/destruction

BView::BView()
{
	saverect.bottom=saverect.top=saverect.left=saverect.right=0;
	game=new Game();
	newlevel=true;
	screen=start;
	playertime=bombatime=timestart=0;
	::SetCurrentDirectory("C:/BOMBERSYS/");	
	pause=pause1=false;
}

BView::~BView()
{
	if (screen>start)
		delete game;
}

/////////////////////////////////////////////////////////////////////////////
// BView drawing

void BView::OnDraw(CDC* pDC)
{	
	CRect rect;
	GetClientRect(rect);
	if (screen==action)
	{
		if (newlevel)
		{
			KillTimer(ID_TIMER);
			SetTimer(ID_TIMER,10,NULL);
			game->GenLevel();
			newlevel=false;
		}		
		if (rect!=saverect)
		{
			m_VirtScreen.DeleteObject();
			m_VirtScreen.CreateCompatibleBitmap(pDC,rect.Width(),rect.Height());
			m_VirtScreenDC.SelectObject(&m_VirtScreen);		
			saverect=rect;
		}
		game->DrawBmp(&m_VirtScreenDC,playertime==PLAYERSPEED);	

			
		CString str;
		AfxGetMainWnd()->GetWindowText(str);
		

		if (str=="pause")
		{
			pause=true;	
			timestart=0;
			AfxGetMainWnd()->SetWindowText("BOMBERMAN");
		}
		if (str=="game over")
		{
			AfxGetMainWnd()->SetWindowText("BOMBERMAN");
			screen=gameover;
		}
		

		
		if ((pause)&&(timestart<50)) game->DrawPause(&m_VirtScreenDC,false);
		if (pause1) game->DrawPause(&m_VirtScreenDC);
	}
	if (screen==start)
	{
		m_VirtScreenDC.SelectObject(&m_VirtScreen);	
		m_VirtScreen.Detach();
		m_VirtScreen.Attach(game->startbmp);
		m_VirtScreenDC.SelectObject(&m_VirtScreen);		
	}
	if (screen==gameover)
	{
 		m_VirtScreenDC.SelectObject(&m_VirtScreen);	
		m_VirtScreen.Detach();
		m_VirtScreen.Attach(game->gameoverbmp);
		m_VirtScreenDC.SelectObject(&m_VirtScreen);	
	}
	
	pDC->BitBlt(0,0,rect.Width(),rect.Height(),&m_VirtScreenDC,0,0,SRCCOPY);
}
	


/////////////////////////////////////////////////////////////////////////////
// BView diagnostics

#ifdef _DEBUG


Doc* BView::GetDocument() // non-debug version is inline
{
	ASSERT(m_pDocument->IsKindOf(RUNTIME_CLASS(Doc)));
	return (Doc*)m_pDocument;
}
#endif //_DEBUG


int BView::OnCreate(LPCREATESTRUCT lpCreateStruct) 
{
	if (CView::OnCreate(lpCreateStruct) == -1)
		return -1;
	CPaintDC dc(this);
	game->CreateCompatibleDC(dc);
	m_VirtScreenDC.CreateCompatibleDC(&dc);	
	return 0;
}

void BView::OnKeyDown(UINT nChar, UINT nRepCnt, UINT nFlags) 
{
	if (screen==gameover)
	{
		screen=start;  
		Invalidate(true);
		return;
	}
	if (screen==start)
	{
		screen=action;
		Invalidate();
		return;
	}

	if (timestart>50)
	{
	BOOL res=false;
	
	if (game->pl1->move<ltrup)
	{
		if ((nChar==game->pl1->l)) {game->pl1->savemove= game->pl1->move;game->pl1->move=left;	res=true;}	// Смещение влево
		if ((nChar==game->pl1->r)) {game->pl1->savemove= game->pl1->move;game->pl1->move=right;	res=true;}	// Смещение вправо
		if ((nChar==game->pl1->t)) {game->pl1->savemove= game->pl1->move;game->pl1->move=top;	res=true;}	// Смещение вверх
		if ((nChar==game->pl1->b)) {game->pl1->savemove= game->pl1->move;game->pl1->move=bottom;res=true;}	// Смещение вниз
	}
	if (game->pl2->move<ltrup)
	{	
		if ((nChar==game->pl2->l)) {game->pl2->savemove= game->pl2->move;game->pl2->move=left;res=true;}
		if ((nChar==game->pl2->r)) {game->pl2->savemove= game->pl2->move;game->pl2->move=right;res=true;}
		if ((nChar==game->pl2->t)) {game->pl2->savemove= game->pl2->move;game->pl2->move=top;res=true;}
		if ((nChar==game->pl2->b)) {game->pl2->savemove= game->pl2->move;game->pl2->move=bottom;res=true;}
	}
	/////// Установка бомбы
	int k=0;
	if ((nChar==game->pl1->bum)&&(game->pl1->n_bomb>0)&&(game->pl1->move<ltrup)&&(game->pl1->active)) 
	{
		char i=char(game->pl1->cpxy.x/49);
		char j=char(game->pl1->cpxy.y/49);
		char dx=char((game->pl1->cpxy.x-i*49)/7);
		char dy=char((game->pl1->cpxy.y-j*49)/7);
		
		if ((dx==3)||(dy==3))
			return;

		game->pl1->n_bomb--;
		for(k=0;k<10;k++)
		{
			if ((game->bomb[k]!=NULL)&&(game->bomb[k]->player1==true)&&(game->bomb[k]->active==false)) break;
		}

		game->bomb[k]->active=true;
		game->bomb[k]->cpxy.x=i*49;
		game->bomb[k]->cpxy.y=j*49;
		
	
		if (dx>3)
			game->bomb[k]->cpxy.x+=49;
		
		//if (dx==3)
		//	game->bomb[k]->cpxy.x+=25;
			
		if (dy>3)
			game->bomb[k]->cpxy.y+=49;
		
		//if (dy==3)
		//	game->bomb[k]->cpxy.y+=28;

		for(int t=0;t<10;t++)
		{
			if ((t!=k)&&(game->bomb[t]!=NULL)&&(game->bomb[t]->cpxy==game->bomb[k]->cpxy)&&(game->bomb[t]->active==true)) 
			{
				game->bomb[k]->active=false;
				game->pl1->n_bomb++;
			}

		}			
		res=true;
		if (game->bomb[k]->active==true)
			game->FrontBomb(game->bomb[k]);
	}	
	if ((nChar==game->pl2->bum)&&(game->pl2->n_bomb>0)&&(game->pl2->move<ltrup)&&(game->pl2->active)) 
	{		
		
		char i=char(game->pl2->cpxy.x/49);
		char j=char(game->pl2->cpxy.y/49);
		char dx=char((game->pl2->cpxy.x-i*49)/7);
		char dy=char((game->pl2->cpxy.y-j*49)/7);
		
		if ((dx==3)||(dy==3))
			return;

		game->pl2->n_bomb--;
		for(k=0;k<10;k++)
		{
			if ((game->bomb[k]!=NULL)&&(game->bomb[k]->player1==false)&&(game->bomb[k]->active==false)) break;
		}
		game->bomb[k]->active=true;	
		game->bomb[k]->cpxy.x=i*49;
		game->bomb[k]->cpxy.y=j*49;

		if (dx>3)
			game->bomb[k]->cpxy.x+=49;
	//	if (dx==3)
	//		game->bomb[k]->cpxy.x+=25;
		
		
		if (dy>3)
			game->bomb[k]->cpxy.y+=49;
	//	if (dy==3)
	//		game->bomb[k]->cpxy.y+=28;
		for(int t=0;t<10;t++)
		{
			if ((t!=k)&&(game->bomb[t]!=NULL)&&(game->bomb[t]->cpxy==game->bomb[k]->cpxy)&&(game->bomb[t]->active==true)) 
			{
				game->bomb[k]->active=false;
				game->pl2->n_bomb++;

			}

		}
		res=true;	
		if (game->bomb[k]->active==true)
			game->FrontBomb(game->bomb[k]);
	}

	///////////////////////////////////////////////////////////////////
	/////////////////////| DEBUG BLOCK             |///////////////////
	/*
	// Вызов суперсмерти игроков
	if (nChar==70)			 {game->pl2->savemove= game->pl2->move;game->pl2->move=sltrup;  game->pl2->kadr=21;	game->pl2->timetrupx=0;  res=true;}
	if (nChar==72)			 {game->pl2->savemove= game->pl2->move;game->pl2->move=srtrup;  game->pl2->kadr=0;	game->pl2->timetrupx=0;  res=true;}	
	if (nChar==84)			 {game->pl2->savemove= game->pl2->move;game->pl2->move=sttrup;  game->pl2->kadr=32;	game->pl2->timetrupy=0;  res=true;}
	if (nChar==71)			 {game->pl2->savemove= game->pl2->move;game->pl2->move=sbtrup;  game->pl2->kadr=22; game->pl2->timetrupy=0;	 res=true;}
	if (nChar==70)			 {game->pl1->savemove= game->pl1->move;game->pl1->move=sltrup;  game->pl1->kadr=21;	game->pl1->timetrupx=0;  res=true;}
	if (nChar==72)			 {game->pl1->savemove= game->pl1->move;game->pl1->move=srtrup;  game->pl1->kadr=0;	game->pl1->timetrupx=0;  res=true;}	
	if (nChar==84)			 {game->pl1->savemove= game->pl1->move;game->pl1->move=sttrup;  game->pl1->kadr=32;	game->pl1->timetrupy=0;  res=true;}
	if (nChar==71)			 {game->pl1->savemove= game->pl1->move;game->pl1->move=sbtrup;  game->pl1->kadr=22; game->pl1->timetrupy=0;  res=true;}
	
	// Вызов смерти игроков
	if (nChar==74)			 {game->pl2->savemove= game->pl2->move;game->pl2->move=ltrup;  game->pl2->kadr=0;	game->pl2->timetrupx=0;	 res=true;}
	if (nChar==76)			 {game->pl2->savemove= game->pl2->move;game->pl2->move=rtrup;  game->pl2->kadr=29;	game->pl2->timetrupx=0;  res=true;}	
	if (nChar==73)			 {game->pl2->savemove= game->pl2->move;game->pl2->move=ttrup;  game->pl2->kadr=30;	game->pl2->timetrupy=0;  res=true;}
	if (nChar==75)			 {game->pl2->savemove= game->pl2->move;game->pl2->move=btrup;  game->pl2->kadr=44;	game->pl2->timetrupy=0;  res=true;}
	if (nChar==74)			 {game->pl1->savemove= game->pl1->move;game->pl1->move=ltrup;  game->pl1->kadr=0;	game->pl1->timetrupx=0;	 res=true;}
	if (nChar==76)			 {game->pl1->savemove= game->pl1->move;game->pl1->move=rtrup;  game->pl1->kadr=29;	game->pl1->timetrupx=0;  res=true;}	
	if (nChar==73)			 {game->pl1->savemove= game->pl1->move;game->pl1->move=ttrup;  game->pl1->kadr=30;	game->pl1->timetrupy=0;  res=true;}
	if (nChar==75)			 {game->pl1->savemove= game->pl1->move;game->pl1->move=btrup;  game->pl1->kadr=44;	game->pl1->timetrupy=0;  res=true;}
	*/
	//if (nChar==77) game->Print();// Показать матрицу!




	// Pause (P)
	if (nChar==80) 
	{
		if (!pause1)
		{
			KillTimer(ID_TIMER);
			pause1=true;
			//game->Print();// DEBUG
		}
		else
		{
			SetTimer(ID_TIMER,10,NULL);
			pause1=false;
		}
		res=true;
		
	}


	CString str;
	str.Format("key=%i (%c)",nChar,char(nChar));
	//AfxMessageBox(str);
    //////////////////////////////////////////////////////////////////
	/////////////////////////////////////////////////////////////////

	if(res) Invalidate();
	CView::OnKeyDown(nChar, nRepCnt, nFlags);
	}
}

void BView::OnTimer(UINT nIDEvent) 
{
	if (timestart>50)
	{
	playertime++;
	bombatime++;
	// Перерисовка игрока №1
	if (playertime==1)
	{	
		game->pl1->savecpxy=game->pl1->cpxy;
		//if (game->pl1->move!=stop)	
			game->pl1->NextStep(game->Matrix,game->bonus);
			
		// НЕДОПУСТИМЫЙ ЗАХОД НА БОМБУ И ИГРОКА
		for(int k=0;k<10;k++)
		{
			if ((game->bomb[k]!=NULL)&&(game->bomb[k]->active==true)&&(game->bomb[k]->kadr>0)&&(game->bomb[k]->kadr<5)) 
			{
					// расстояние не должно уменьшаться меньше 30, но может увеличиваться с нуля.
					int l=game->L(game->bomb[k]->cpxy,game->pl1->cpxy);
					if ((l<30)&&(game->L(game->bomb[k]->cpxy,game->pl1->savecpxy)>30))
						
						game->pl1->cpxy=game->pl1->savecpxy;
			}	
		}
		if (game->pl2->active)
		{
				if ((game->L(game->pl2->cpxy,game->pl1->cpxy)<20)&&(game->pl2->move<ltrup))
					game->pl1->cpxy=game->pl1->savecpxy;
	
		}

		
	}
	// Перерисовка игрока №2, если он активен
	if ((playertime==2)&&(game->pl2->active))
	{
		game->pl2->savecpxy=game->pl2->cpxy;
		//if (game->pl2->move!=stop)	
			game->pl2->NextStep(game->Matrix,game->bonus);
		
		// НЕДОПУСТИМЫЙ ЗАХОД НА БОМБУ И ДРУГОГО ИГРОКА
		for(int k=0;k<10;k++)
		{
			if ((game->bomb[k]!=NULL)&&(game->bomb[k]->active==true)&&(game->bomb[k]->kadr>0)&&(game->bomb[k]->kadr<5)) 
			{
				int l=game->L(game->bomb[k]->cpxy,game->pl2->cpxy);
				if ((l<30)&&(game->L(game->bomb[k]->cpxy,game->pl2->savecpxy)>30))
					game->pl2->cpxy=game->pl2->savecpxy;
				
			}	
		}
		if (game->pl1->active)
		{
				if ((game->L(game->pl2->cpxy,game->pl1->cpxy)<20)&&(game->pl1->move<ltrup))
					game->pl2->cpxy=game->pl2->savecpxy;
	
		}
		
	}

	if (bombatime==3)
	{
		for(int k=0;k<10;k++)
		{
			if ((game->bomb[k]!=NULL)&&(game->bomb[k]->active==true)) 
			{
				if (game->bomb[k]->NextStep())
				{
					if (game->bomb[k]->player1)
						game->pl1->n_bomb++;
					else
						game->pl2->n_bomb++;
				}
			}
			
		}

	}
	if (playertime==PLAYERSPEED) playertime=0;
	if (bombatime==BOMBASPEED) bombatime=0;
	}
	else timestart++;

	Invalidate(true);
	//CView::OnTimer(nIDEvent);
}

void BView::OnKeyUp(UINT nChar, UINT nRepCnt, UINT nFlags) 
{
	/////////////| STOP только если текущее(последнее нажатое) направление отменено
	if ((nChar==game->pl1->l)&&(game->pl1->move==left))		{game->pl1->move=stop;} 
	if ((nChar==game->pl1->r)&&(game->pl1->move==right))	{game->pl1->move=stop;}
	if ((nChar==game->pl1->t)&&(game->pl1->move==top))		{game->pl1->move=stop;}
	if ((nChar==game->pl1->b)&&(game->pl1->move==bottom))	{game->pl1->move=stop;}

	if ((nChar==game->pl2->l)&&(game->pl2->move==left))		{game->pl2->move=stop;} 
	if ((nChar==game->pl2->r)&&(game->pl2->move==right))	{game->pl2->move=stop;}
	if ((nChar==game->pl2->t)&&(game->pl2->move==top))		{game->pl2->move=stop;}
	if ((nChar==game->pl2->b)&&(game->pl2->move==bottom))	{game->pl2->move=stop;}
	
	CView::OnKeyUp(nChar, nRepCnt, nFlags);
}
