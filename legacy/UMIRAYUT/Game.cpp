// Game.cpp: implementation of the Game class.
//
//////////////////////////////////////////////////////////////////////////////////////////////////////////////
//|									СПРАВОЧНИК ПО ЭЛЕМЕНТАМ МАТРИЦЫ
//|///////////////////////////////////////////////////////////////////////////////////////////////////////////
//|
//|  10 - пустая клетка (11,12,13,14- наслоение фронта взрыва)
//|  80 - стенка 
//|  99 - неуязвимая стенка
//|  <50 проходимые клетки
//|
//|
//|
//|
/////////////////////////////////////////////////////////////////////////////////////////////////////////////*

#include "stdafx.h"
#include "Game.h"
#include "Player.h"
#include "Bomb.h"
#include "Bonus.h"

#include <math.h>
#define POL RGB(100,100,100)
//#define POL RGB(255,255,255)

#ifdef _DEBUG
#undef THIS_FILE
static char THIS_FILE[]=__FILE__;
#define new DEBUG_NEW
#endif
Game::L(CPoint &cp1,CPoint &cp2)
{
	return int(sqrt((cp1.x-cp2.x)*(cp1.x-cp2.x)+(cp1.y-cp2.y)*(cp1.y-cp2.y)));
}
 void Game::Print()
 {
 	CString str,str1;

 	for(int i=0;i<=14;i++)
 	{
 		for(int j=0;j<=14;j++)
 		{	
 			str1.Format("%i ",Matrix[i][j]);
			str+=str1;
 		}	
 		str+="\n";
 	}
	//s=str;
	AfxMessageBox(str);
}
//////////////////////////////////////////////////////////////////////
// Construction/Destruction
//////////////////////////////////////////////////////////////////////
//
//  10 пустая
//  99 несгораемая
//  80 обычная стенка
// Меньше 20 - проходимые для существ клетки!!!!
//
Game::Game()
{		
	/////////////////////////////////////////////
	//| Начальные настройки игроков
	pl1=new Player(true, "","FACE.BMP PLAYER1.BMP TRUP1.BMP SUPERTRUP1.BMP plus1.bmp",65,68,87,83,32,0,0,true);
	pl2=new Player(false,"","FACE1.BMP PLAYER2.BMP TRUP2.BMP SUPERTRUP2.BMP plus2.bmp",37,39,38,40,46,14,14,true);
	//////////////////////////////////////////////

	// Создание и инициализация матрицы 
	Matrix=new char *[15];
	// Создание бомб
	for(int i=0;i<10;i++)
	{
		if (i<5)
			bomb[i]=new Bomb(true,0,0,false);	
		else	
			bomb[i]=new Bomb(false,0,0,false);	

	}
	for(i;i<10;i++)
	bomb[i]=NULL;
	level=0;
	
	// Создание бонусов
	//enum Sort {door,sunduk,bomb,live,smert,meshok,bigmeshok,bruliki,nasledstvo};
	srand(time(NULL));rand();
	
	int	num=int((2*(double)rand()/RAND_MAX));

	bonus[0]=new Bonus(door);
	bonus[1]=new Bonus(sunduk);
	bonus[2]=new Bonus(bomba);
	if (num==1)
		bonus[3]=new Bonus(live);
	else
		bonus[3]=new Bonus(smert);	
	
	for(i=4;i<9;i++)
	{
		num=int((3*(double)rand()/RAND_MAX));
		if (num==0) bonus[i]=new Bonus(meshok);
		if (num==1) bonus[i]=new Bonus(bigmeshok);
		if (num>1) bonus[i]=new Bonus(bruliki);
	}
	bonus[9]=new Bonus(nasledstvo);


	font.CreateFont(
		   24,                        // nHeight
		   10,                        // nWidth
		   0,                         // nEscapement
		   0,                         // nOrientation
		   FW_NORMAL,                 // nWeight
		   FALSE,                     // bItalic
		   FALSE,                     // bUnderline
		   0,                         // cStrikeOut
		   DEFAULT_CHARSET,           // nCharSet
		   OUT_DEFAULT_PRECIS,        // nOutPrecision
		   CLIP_DEFAULT_PRECIS,       // nClipPrecision
		   PROOF_QUALITY,             // nQuality
		   DEFAULT_PITCH | FF_SWISS,  // nPitchAndFamily
		   "Arial");                  // lpszFacename
		bigfont.CreateFont(
		   36,                        // nHeight
		   15,                        // nWidth
		   0,                         // nEscapement
		   0,                         // nOrientation
		   FW_NORMAL,                 // nWeight
		   FALSE,                     // bItalic
		   FALSE,                     // bUnderline
		   0,                         // cStrikeOut
		   DEFAULT_CHARSET,           // nCharSet
		   OUT_DEFAULT_PRECIS,        // nOutPrecision
		   CLIP_DEFAULT_PRECIS,       // nClipPrecision
		   PROOF_QUALITY,             // nQuality
		   DEFAULT_PITCH | FF_SWISS,  // nPitchAndFamily
		   "Arial");                  // lpszFacename
	HINSTANCE hInst = AfxGetInstanceHandle();// Для буфера
	plusbmp		= (HBITMAP)::LoadImage(hInst,	"plus.bmp",		IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	bumbmp		= (HBITMAP)::LoadImage(hInst,	"Bumbomb.BMP",	IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	bomb1bmp	= (HBITMAP)::LoadImage(hInst,	"Bomb1.BMP",	IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	bomb2bmp	= (HBITMAP)::LoadImage(hInst,	"Bomb2.BMP",	IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	pausebmp	= (HBITMAP)::LoadImage(hInst,	"pause.BMP",	IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	pause1bmp	= (HBITMAP)::LoadImage(hInst,	"pause1.BMP",	IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	startbmp	= (HBITMAP)::LoadImage(hInst,	"start.BMP",	IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	gameoverbmp	= (HBITMAP)::LoadImage(hInst,	"gameover.BMP",	IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	
	bum1bmp	= (HBITMAP)::LoadImage(hInst,	"bum1.BMP",	IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	bum2bmp	= (HBITMAP)::LoadImage(hInst,	"bum2.BMP",	IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
}

Game::~Game()
{
	delete pl1,pl2;
	m_VirtScreen.DeleteObject();
	TempScreen.DeleteObject();
	DeleteDC (TempScreenDC);
	DeleteDC (m_VirtScreenDC);
	//Удаление матрицы
	for(int k=0;k<15;++k) 
		delete Matrix[k];
	delete  [] Matrix;
	
	for(k=0;k<10;k++)
	{
		if (bomb[k]!=NULL) delete bomb[k];
		bomb[k]=NULL;
		if (bonus[k]!=NULL) delete bonus[k];
		bonus[k]=NULL;
	}
}

void Game::CreateCompatibleDC(CPaintDC &dc)
{
	m_VirtScreenDC.CreateCompatibleDC(&dc);	
	TempScreenDC.CreateCompatibleDC(&dc);
}
//////////////////////////////////////////////////////////////////////////////////////
//**********************************************************************************//
//*         БЛОК ГЕНЕРАЦИИ УРОВНЯ:(GenLevel,GenMatrix,GenBmp)				   *//
//**********************************************************************************//
//////////////////////////////////////////////////////////////////////////////////////
void Game::GenLevel() // ГЕНЕРАЦИЯ УРОВНЯ С СОХРАНЕНИЕМ В ВИРТУАЛЬНЫЙ ЭКРАН
{
	CRect rect;
	AfxGetMainWnd()->GetClientRect(rect);
	HINSTANCE hInst = AfxGetInstanceHandle();// Для буфера
	HBITMAP hbm;	
	CPen BluePen(0,5,RGB(0,0,200)),WhitePen(0,1,RGB(255,255,255));

		// Начальные значения экранов!
		m_VirtScreen.DeleteObject();
		TempScreen.DeleteObject();	
		
		hbm = (HBITMAP)::LoadImage(hInst, "22.BMP", IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
		m_VirtScreen.Attach(hbm);
		hbm = (HBITMAP)::LoadImage(hInst, "2.BMP", IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
		TempScreen.Attach(hbm);
		
		m_VirtScreenDC.SelectObject(&m_VirtScreen);	
		TempScreenDC.SelectObject(&TempScreen);
		///////////////////////////////////////////////////////
	
		// Синий прямоугольник
		m_VirtScreenDC.SelectObject(BluePen);
		m_VirtScreenDC.MoveTo(1,1);
		m_VirtScreenDC.LineTo(1,741);
		m_VirtScreenDC.LineTo(741,741);
		m_VirtScreenDC.LineTo(741,1);
		m_VirtScreenDC.LineTo(1,1);
		
		m_VirtScreenDC.SelectObject(WhitePen);
	//	m_VirtScreenDC.SelectObject(WhitePen); //Без рамочек вокруг несгораемых стенок
		int k1,k2;
		k1=k2=1;
		CBrush WhiteBrush(RGB(255,255,255));
		for(int i=4;i<=739;i+=49)
		{
			k1=-k1;
			for(int j=4;j<=739;j+=49)
			{
				k2=-k2;
				if (((k2<0)||(k1<0))&&(i<739)&&(j<739))
				{
					
					CRect rect(i,j,i+49,j+49);
					m_VirtScreenDC.FillRect(rect,&WhiteBrush);
				}
				if (((k2>0)&&(k1>0))&&(i<739)&&(j<739))
				{		
					TempScreenDC.Rectangle(i,j,i+49,j+49); // Несгораемые стены
				}
			}
		}
		WhiteBrush.DeleteObject();

	//Обычные стены
	m_VirtScreenDC.BitBlt(3,3,rect.Width()-285,rect.Height()-9,&TempScreenDC,3,3,SRCAND);

	// Правая панель "космический взрыв"	
	hbm = (HBITMAP)::LoadImage(hInst, "3.BMP", IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	TempScreen.Detach();
	TempScreen.Attach(hbm);
	TempScreenDC.SelectObject(&TempScreen);		
	m_VirtScreenDC.BitBlt(rect.Width()-279,0,rect.Width(),rect.Height(),&TempScreenDC,0,0,SRCCOPY);
	

	WhitePen.DeleteObject();
	BluePen.DeleteObject();

	/////////////
	level++;
	GenMatrix(40);
	GenBmp();
	
	// Создание бонусов
	//enum Sort {door,sunduk,bomb,live,smert,meshok,bigmeshok,bruliki,nasledstvo};
	srand(time(NULL));rand();
	
	int	num=int((2*(double)rand()/RAND_MAX));

	if (num==1)
		bonus[3]->sort=live;
	else
		bonus[3]->sort=smert;	
	
	for(i=4;i<9;i++)
	{
		num=int((3*(double)rand()/RAND_MAX));
		if (num==0) bonus[i]->sort=meshok;
		if (num==1) bonus[i]->sort=bigmeshok;
		if (num>1) bonus[i]->sort=bruliki;
	}
	for(i=0;i<10;i++)
	{
		if (bomb[i]->active)
		{
			if (bomb[i]->player1) pl1->n_bomb++;
			else pl2->n_bomb++;
			bomb[i]->active=false;
		}
		bomb[i]->kadr=bomb[i]->savekadr=0;
		bonus[i]->active=false;
		bonus[i]->on_off=true;
		bonus[i]->ReplaceBmp();
		for(int ii=0;ii<9;ii++)
			bomb[i]->bumb[ii].x=-100;
	}
	pl1->kadr=13;
	pl2->kadr=0;
	pl1->cpxy.x=0;
	pl1->cpxy.y=0;
	pl2->cpxy.x=14*49;
	pl2->cpxy.y=14*49;
	pl1->move=stop;
	pl2->move=stop;
	pl1->stoptrup=false;
	pl2->stoptrup=false;
	AfxGetMainWnd()->SetWindowText("pause");

}
//////////////////////////////////////////////////////////////////////////////////
void Game::GenMatrix(int n)  // Заполнение матрицы хаотично расположенными стенами
{ //(часть генерации уровня, вынесена на всякий случай как законченный блок)
	int kol=0,num=0,n_bonus=0;
	srand(time(NULL));rand();
	int i,j,k1,k2;
	k1=1;
	k2=-1;
	if (n>176) n=176;
	for(int a1=0;a1<=14;a1++)
	{
		Matrix[a1]=new char[15];
		k1=-k1;
		for(int a2=0;a2<=14;a2++)
		{	
			k2=-k2;
			if ((k2>0)&&(k1>0))
				Matrix[a1][a2]=99;
			else 
				Matrix[a1][a2]=10;
		}			
	}
	while (kol<n)
	{
		num=int((225*(double)rand()/RAND_MAX));

		i=int(num/15);
		j=num-int(num/15)*15;
		if (Matrix[i][j]==10)
		{
			if (n_bonus<9)
			{
				Matrix[i][j]=90;
				n_bonus++;
			}
			else
				Matrix[i][j]=80;
			kol++;
			if ((i*j==0)&&(i<2)&&(j<2)) n_bonus--;
			if (pl2->active)
				if ( (i>12)&&(j>12)&&((i*j==196)||(i*j==182))) n_bonus--;
		}
	}
	//Место для игрока 1
	Matrix[0][0]=10;
	Matrix[0][1]=10;
	Matrix[1][0]=10;
	////////////////
	//Место для игрока 2
	if (pl2->active)
	{
		Matrix[14][14]=10;
		Matrix[14][13]=10;
		Matrix[13][14]=10;
	}
	
	////////////////
	//Print();
}

//////////////////////////////////////////////////////////////////////////////////
void Game::GenBmp()// Заполнение буфера экрана по матрице
{//(часть генерации уровня, вынесена на всякий случай как законченный блок)
	CBrush  BlackBrush(POL);	
	m_VirtScreenDC.SelectObject(BlackBrush);
	/*
	HINSTANCE hInst = AfxGetInstanceHandle();// Для буфера
	HBITMAP hbm;	
	hbm = (HBITMAP)::LoadImage(hInst, "POL.BMP", IMAGE_BITMAP,0, 0, LR_DEFAULTSIZE|LR_LOADFROMFILE);
	TempScreen.Detach();
	TempScreen.Attach(hbm);
	TempScreenDC.SelectObject(&TempScreen);	*/	//Картинка на пол
	int l,m;
	l=m=0;
	CRect lrect;
	
	for(int i=4;i<738;i+=49)
	{
		l++;
		for(int j=4;j<738;j+=49)
		{
			m++;
			if (Matrix[m-1][l-1]==10)
			{
				lrect.left=i;
				lrect.right=i+49;
				lrect.top=j;
				lrect.bottom=j+49;		
			//	m_VirtScreenDC.BitBlt(i,j,49,49,&TempScreenDC,i,j,SRCCOPY);
				m_VirtScreenDC.FillRect(lrect,&BlackBrush);// Остальные стены
			}
		}
		m=0;
	}
	BlackBrush.DeleteObject();
}

///////////////////////////////////////////////////////////////////////////////////////////
//***************************************************************************************//
//*            БЛОК ПРОРИСОВКИ УРОВНЯ:(DrawPause,DrawBmp,DrawPlayer,DrawOther,DrawBomb) *//
//***************************************************************************************//
/////////////////////////////////////////////////////////////////////////////| Прорисовка игры, вызывается из OnDraw
void Game::DrawPause(CDC *pDC,bool b)
{
	if (b)
	{
		TempScreen.Detach();
		TempScreen.Attach(pausebmp);
		TempScreenDC.SelectObject(&TempScreen);		
		pDC->BitBlt(315,340,116,66,&TempScreenDC,0,0,SRCCOPY);
	}
	else
	{
		TempScreen.Detach();
		TempScreen.Attach(pause1bmp);
		TempScreenDC.SelectObject(&TempScreen);		
		pDC->BitBlt(250,340,250,66,&TempScreenDC,0,0,SRCCOPY);
	}
}

void Game::DrawBmp(CDC *pDC,bool drowplayer)
{

	CRect rect;
	AfxGetMainWnd()->GetClientRect(rect);

	
	// ПРОРИСОВКА НОВОГО УРОВНЯ???
	if (((pl1->stoptrup)&&(pl2->stoptrup))||((!pl1->active)&&(!pl2->active))||((!pl1->active)&&(pl2->stoptrup))||((!pl2->active)&&(pl1->stoptrup)))
	{
			if (pl1->n_live>0) pl1->active=true;
				else pl1->active=false;
			if (pl2->n_live>0) pl2->active=true;
				else pl2->active=false;
			bonus[0]->active=false;
			if ((pl1->move>=ltrup)&&(pl2->move>=ltrup)) level--;
		
			
			if ((!pl1->active)&&(!pl2->active))
			{
				AfxGetMainWnd()->SetWindowText("game over");
				pl1->n_live=5;pl2->n_live=5;
				level=1 ;
			}
			else
				GenLevel();
	}
	else
	{

			//| (1) Прорисовка основного фона (стены,пол)
			pDC->BitBlt(0,0,rect.Width(),rect.Height(),&m_VirtScreenDC,0,0,SRCCOPY);	
				
			for(int k=0;k<9;k++)	//Прорисовка размещённых, но не собранных бонусов
			{
				if ((bonus[k]!=NULL)&&(bonus[k]->active)&&(bonus[k]->on_off))
 					DrawBonus(bonus[k],pDC);	
			}

			//| (2) Бомбы+взрывы
			for(k=0;k<10;k++)// брызги от взрыва
			{
				if ((bomb[k]!=NULL)&&(bomb[k]->active))
					DrawBomb(bomb[k],pDC);		
			}
			for(k=0;k<10;k++)	// сам взрыв
			{
				if ((bomb[k]!=NULL)&&(bomb[k]->active))
					if (bomb[k]->kadr>=5) DrawBomb(bomb[k],pDC,false);		
			}



			
			//| (3) Запонение правой игровой панели
			DrawOther(pDC);
			

			//| (4) Прорисовка игроков (порядок видимости)
			if ((pl1->move<ltrup)&&(pl2->move<ltrup))
			{
				if ((pl1->cpxy.y<pl2->cpxy.y))
				{
					if (pl1->active) DrawPlayer(pl1,pDC);
					if (pl2->active) DrawPlayer(pl2,pDC);
				}
				else
				{
					if (pl2->active) DrawPlayer(pl2,pDC);
					if (pl1->active) DrawPlayer(pl1,pDC);
				}
			}
			else
			{
				if (pl1->move>=ltrup)
				{
					if (pl1->active) DrawPlayer(pl1,pDC);
					if (pl2->active) DrawPlayer(pl2,pDC);
				}		
				else
				{
						if (pl2->active) DrawPlayer(pl2,pDC);
						if (pl1->active) DrawPlayer(pl1,pDC);
				}
			}
			if ((bonus[9]->active)&&(bonus[9]->on_off))
					DrawBonus(bonus[9],pDC);	
			

			//////////////////////////////////////////////////////////////////////	
			//| DEBUG
		//	CString str;
		//	str.Format("dx=%i,dy=%i",(pl1->cpxy.x-49*(pl1->cpxy.x/49))/7,(pl1->cpxy.y-49*(pl1->cpxy.y/49))/7);
		//	pDC->TextOut(500,500,str);
			//////////////////////////////////////////////////////////////////////
	}

}

/////////////////////////////////////////////////////////////////////////////| Прорисовка игрока
void Game::DrawPlayer(Player *pl,CDC *pDC)
{	
	
	TempScreen.Detach();

	if (pl->move<sltrup)
	{
		if (pl->move<ltrup) TempScreen.Attach(pl->playerbmp);
		else TempScreen.Attach(pl->trupbmp);
		TempScreenDC.SelectObject(&TempScreen);	

		TransparentBlt(pDC->m_hDC,					// На что накладываем
				   pl->cpxy.x+4,pl->cpxy.y+4,49,49, // Кусок картинки
				   TempScreenDC.m_hDC,              // Что накладываем
				   int(pl->kadr)*50, 0,49,49,       // Кусок картинки
				   RGB(255,255,255));				// Полупрозрачность-> Белый прозрачный фон.
	}
	else 
	{
		TempScreen.Attach(pl->strupbmp);
		TempScreenDC.SelectObject(&TempScreen);	

		TransparentBlt(pDC->m_hDC,						// На что накладываем
				   pl->cpxy.x+4,pl->cpxy.y+6-15,64,64,  // Кусок картинки
				   TempScreenDC.m_hDC,					// Что накладываем
				   int(pl->kadr)*65, 0,64,64,           // Кусок картинки
				   RGB(255,255,255));					// Полупрозрачность-> Белый прозрачный фон.
	}

	//////////////////////////////////////////////////////////////////////////////////
	//| Физиономия игрока и его параметры	
	TempScreen.Detach();
	TempScreen.Attach(pl->facebmp);
	TempScreenDC.SelectObject(&TempScreen);	

	pDC->BitBlt(760,405+170*(!pl->player1),108,150,&TempScreenDC,0,0,SRCCOPY);
	// Параметры игрока
	TempScreen.Detach();
	TempScreen.Attach(pl->plusbmp);
	TempScreenDC.SelectObject(&TempScreen);	

	pDC->BitBlt(890,405+170*(!pl->player1),108,150,&TempScreenDC,0,0,SRCCOPY);
	TempScreen.Detach();
	

	pDC->SetBkColor(RGB(21,9,54));
	pDC->SetTextAlign(TA_CENTER);
	pDC->SetBkMode(OPAQUE);
	pDC->SelectObject(font);
	pDC->SetTextColor(RGB(0,150,255));
	CRect rect(805,405+170*(!pl->player1)+125,860,405+170*(!pl->player1)+149);	
	pDC->ExtTextOut(805,405+170*(!pl->player1)+125,ETO_OPAQUE,rect,pl->nameplayer,pl->nameplayer.GetLength(),NULL);
	
	CString str;
	// Количество очков
	str.Format("%i",pl->score);
	pDC->TextOut(940,530+170*(!pl->player1),str);
	pDC->SelectObject(bigfont);
	pDC->SetBkColor(RGB(192,192,192));
	// Количество жизней
	str.Format("%i",pl->n_live);
	pDC->TextOut(975,426+170*(!pl->player1),str);
	// Количество бомб
	str.Format("%i",pl->n_bomb);
	pDC->TextOut(975,476+170*(!pl->player1),str);
}


/////////////////////////////////////////////////////////////////////////////| Прорисовка правой панели и т.п.
void Game::DrawOther(CDC *pDC)
{	
	CFont f1;
		f1.CreateFont(
		   30,                        // nHeight
		   12,
		   0,                         // nEscapement
		   0,                         // nOrientation
		   FW_NORMAL,                 // nWeight
		   FALSE,                     // bItalic
		   FALSE,                     // bUnderline
		   0,                         // cStrikeOut
		   DEFAULT_CHARSET,           // nCharSet
		   OUT_DEFAULT_PRECIS,        // nOutPrecision
		   CLIP_DEFAULT_PRECIS,       // nClipPrecision
		   PROOF_QUALITY,             // nQuality
		   DEFAULT_PITCH | FF_SWISS,  // nPitchAndFamily
		   "Arial");                  // lpszFacename
	pDC->SelectObject(f1);
	TempScreen.Detach();
	TempScreen.Attach(plusbmp);
	TempScreenDC.SelectObject(&TempScreen);	
	
	pDC->BitBlt(760,10,324,150,&TempScreenDC,0,0,SRCCOPY);


	CString str;
	pDC->SetBkColor(RGB(192,192,192));
	pDC->SetTextColor(RGB(155,0,0));
	str.Format("Уровень %i",level);
	pDC->TextOut(880,16,str);
	pDC->SetTextColor(RGB(0,150,255));
}


/////////////////////////////////////////////////////////////////////////////| Прорисовка бомб и взрывов
void Game::DrawBomb(Bomb *b,CDC *pDC,bool b1)
{	
	int i=char(b->cpxy.x/49);
	int j=char(b->cpxy.y/49)+1;

	
	if (b->kadr<5) // До пятого кадра динамит, после взрыв!
	{
		TempScreen.Detach();
		if (b->player1)
			TempScreen.Attach(bomb1bmp);	
		else
			TempScreen.Attach(bomb2bmp);	
		TempScreenDC.SelectObject(&TempScreen);	

		TransparentBlt(pDC->m_hDC,						// На что накладываем
				   b->cpxy.x+4,b->cpxy.y+4,49,49, // Кусок картинки
				   TempScreenDC.m_hDC,              
				   int(b->kadr)*50, 0,49,49,         
				   RGB(255,255,255));			
	}
	else 
	{
		if (b1)
		{
			// ВЗРЫВ БЛИЖНЕГО РАДИУСА
			if ((b->kadr>=6)&&(b->kadr<=14))
				{
					TempScreen.Detach();
					TempScreen.Attach(bum1bmp);	
					TempScreenDC.SelectObject(&TempScreen);	
					
					for(int i=1;i<5;i++)
					{
						if (b->bumb[i].x>=0)
						{
							TransparentBlt(pDC->m_hDC,b->bumb[i].x*49+4,b->bumb[i].y*49+4,49,49,TempScreenDC.m_hDC,0, 0,49,49,RGB(255,255,255));
							
							//ВЗРЫВ СТЕНЫ!!!!
							if ((b->kadr==10)&&(Matrix[b->bumb[i].y][b->bumb[i].x]>=80)&&(Matrix[b->bumb[i].y][b->bumb[i].x]<99))
							{
								

								CBrush  BlackBrush(POL);	
								m_VirtScreenDC.SelectObject(BlackBrush);
								CRect lrect;
								lrect.left=b->bumb[i].x*49+4;
								lrect.right=b->bumb[i].x*49+53;
								lrect.top=b->bumb[i].y*49+4;
								lrect.bottom=b->bumb[i].y*49+53;		
								m_VirtScreenDC.FillRect(lrect,&BlackBrush);// стена исчезла в буфере
								BlackBrush.DeleteObject();

								// Взорвали стену с бонусом-> выбираем бонус
								if ((Matrix[b->bumb[i].y][b->bumb[i].x]>=90)&&(Matrix[b->bumb[i].y][b->bumb[i].x]<99))
								{
									srand(time(NULL));rand();
									int num=int((9*(double)rand()/RAND_MAX));
									
								int o=0;
								//	CString str;

									while ((bonus[num]->active==true)&&(o<100))
									{
									
										num=int((9*(double)rand()/RAND_MAX));
										o++;
									//	str.Format("%i",o);
									//	AfxGetMainWnd()->SetWindowText(str);
									}
								
									if (o>=100)
									{
											for(int i=0;i<9;i++)
											{
												if (!bonus[i]->active)
												//str.Format("%i",i);
												//AfxGetMainWnd()->SetWindowText(str);
												//AfxMessageBox(str);
												num=i;
												break;
											}
									}



									
									bonus[num]->active=true;
									bonus[num]->cpxy.x=b->bumb[i].x*49;
									bonus[num]->cpxy.y=b->bumb[i].y*49;
													
								}
								Matrix[b->bumb[i].y][b->bumb[i].x]=10;// стена исчезла в матрице
								
							}
							//ВЗРЫВ БОМБ НА БЛИЖНЕМ РАДИУСЕ
							if (!b->bb[0])
							{
								Matrix[b->bumb[i].y][b->bumb[i].x]++;// Отметка в матрице
								for(int k=0;k<10;k++)
								{
									if ((bomb[k]!=NULL)&&(bomb[k]->active))
									{
										if ((bomb[k]->bumb[0]==b->bumb[i])&&(bomb[k]->kadr<5)) 
													bomb[k]->kadr=5;// ускорение взрыва соседней бомбы
									}
								}
							}
						}
						if ((i==4)&&(!b->bb[0])) 
						{
							b->bb[0]=true;
							Matrix[b->bumb[0].y][b->bumb[0].x]++;
						}
									
					}
			}
			// ВЗРЫВ ДАЛЬНЕГО РАДИУСА
			if ((b->kadr>=7)&&(b->kadr<=15))
				{
					TempScreen.Detach();
					TempScreen.Attach(bum2bmp);	
					TempScreenDC.SelectObject(&TempScreen);	

					for(int i=5;i<9;i++)
					{
						if (b->bumb[i].x>=0)
						{
							TransparentBlt(pDC->m_hDC,b->bumb[i].x*49+4,b->bumb[i].y*49+4,49,49,TempScreenDC.m_hDC,0, 0,49,49,RGB(255,255,255));
							//ВЗРЫВ БОМБ НА ДАЛЬНЕМ РАДИУСЕ
							if (!b->bb[1])
							{
								Matrix[b->bumb[i].y][b->bumb[i].x]++;// Отметка в матрице
								for(int k=0;k<10;k++)
								{
									if ((bomb[k]!=NULL)&&(bomb[k]->active))
									{
										if ((bomb[k]->bumb[0]==b->bumb[i])&&(bomb[k]->kadr<5)) 
												bomb[k]->kadr=5;// ускорение взрыва соседней бомбы									
									}
								}
							}
						}
						if (i==8) b->bb[1]=true;
					}
				}
			///////////////////////////////////////////
			// Востановление значений в матрице
			if ((b->kadr==15)&&(!b->bb[2]))
			{
				for(int i=0;i<5;i++)
				{
					if ((b->bumb[i].x>=0)&&(Matrix[b->bumb[i].y][b->bumb[i].x]>10))
						 Matrix[b->bumb[i].y][b->bumb[i].x]--;
				}
				b->bb[2]=true;
			}
			if ((b->kadr==18)&&(!b->bb[3]))
			{
				for(int i=5;i<9;i++)
				{
					if ((b->bumb[i].x>=0)&&(Matrix[b->bumb[i].y][b->bumb[i].x]>10))
						 Matrix[b->bumb[i].y][b->bumb[i].x]--;
				}
				b->bb[3]=true;
			}
			///////////////////////////////////////////
		}
		else
		{
			TempScreen.Detach();	
			TempScreen.Attach(bumbmp);	
			TempScreenDC.SelectObject(&TempScreen);	
			TransparentBlt(pDC->m_hDC,				
					   b->cpxy.x-45,b->cpxy.y-45,147,147, 
					   TempScreenDC.m_hDC,              
					   int(b->kadr)*148, 0,147,147,           
					   RGB(255,255,255));	
		}
	}
}
void Game::DrawBonus(Bonus *b,CDC *pDC)
{	
	int i=char(b->cpxy.x/49);
	int j=char(b->cpxy.y/49)+1;


	TempScreen.Detach();
	TempScreen.Attach(b->bonusbmp);		
	TempScreenDC.SelectObject(&TempScreen);	

	TransparentBlt(pDC->m_hDC,					
				   b->cpxy.x+4,b->cpxy.y+4,49,49, 
				   TempScreenDC.m_hDC,              
				   0, 0,49,49,         
				   RGB(255,255,255));			
	
}
///////////////////////////////////////////////////////////////////////////////////////////
//***************************************************************************************//
//*                ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ:(FrontBomb,TestTrup)                         *//
//***************************************************************************************//

void Game::FrontBomb(Bomb *bomb)
{
	// Зона взрыва- массив bumb
	//        6     
	//        2
	//    5 1 0 3 7
	//		  4	
	//		  8	
	bomb->bb[0]=bomb->bb[1]=bomb->bb[2]=bomb->bb[3]=false;
	/////////////////////////////////////////////////////////////////////
	/////| ЗАПОЛНЕНИЕ ФРОНТА ВЗРЫВА	
	for(int ii=0;ii<9;ii++)
		bomb->bumb[ii].x=-100;	
		int i=char(bomb->cpxy.x/49);
		int j=char(bomb->cpxy.y/49);
		bomb->bumb[0].x=i;
		bomb->bumb[0].y=j;	
		//СВЕРХУ
		if ((i>0)&&(Matrix[j][i-1]!=99))// не скраю и не несгораемая стенка
		{
			bomb->bumb[2].x=i-1;
			bomb->bumb[2].y=j;
			if ((i>1)&&(Matrix[j][i-1]!=80)&&(Matrix[j][i-1]!=90)&&(Matrix[j][i-2]<80))
			{
				bomb->bumb[6].x=i-2;
				bomb->bumb[6].y=j;
			}
		}
		//СЛЕВА
		if ((j>0)&&(Matrix[j-1][i]!=99))// не скраю и не несгораемая стенка
		{
			bomb->bumb[1].x=i;
			bomb->bumb[1].y=j-1;
			if ((j>1)&&(Matrix[j-1][i]!=80)&&(Matrix[j-1][i]!=90)&&(Matrix[j-2][i]<80))
			{
				bomb->bumb[5].x=i;
				bomb->bumb[5].y=j-2;
			}
		}
		//СПРАВА
		if ((i<14)&&(Matrix[j][i+1]!=99))// не скраю и не несгораемая стенка
		{
			bomb->bumb[3].x=i+1;
			bomb->bumb[3].y=j;
			if ((i<13)&&(Matrix[j][i+1]!=80)&&(Matrix[j][i+1]!=90)&&(Matrix[j][i+2]<80))
			{
				bomb->bumb[7].x=i+2;
				bomb->bumb[7].y=j;
			}
		}
		//СНИЗУ
		if ((j<14)&&(Matrix[j+1][i]!=99))// не скраю и не несгораемая стенка
		{
			bomb->bumb[4].x=i;
			bomb->bumb[4].y=j+1;
			if ((j<13)&&(Matrix[j+1][i]!=80)&&(Matrix[j+1][i]!=90)&&(Matrix[j+2][i]<80))
			{
				bomb->bumb[8].x=i;
				bomb->bumb[8].y=j+2;
			}
		}
}





