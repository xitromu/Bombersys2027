// Game.h: interface for the Game class.
//
//////////////////////////////////////////////////////////////////////

#if !defined(AFX_GAME_H__17A04225_47C4_47E9_AC16_A13A869E065C__INCLUDED_)
#define AFX_GAME_H__17A04225_47C4_47E9_AC16_A13A869E065C__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

class Player;
class Bomb;
class Bonus;
enum Move;
enum Sort;

class Game  
{
	public:	
		void CreateCompatibleDC(CPaintDC &dc);			//| Создаёт совместимые с экраном виртуальные экраны: вызывается в BView::OnCreate	
		//** ГЕНЕРАЦИЯ УРОВНЯ(Фона, тварей, бонусов)
		void GenLevel();								//| По матрице отрисовывает в m_VirtScreen.	
		void GenMatrix(int n);							//| Генерация матрицы уровня
		void GenBmp();									//| Генерация по матрице BMP

		//** ОТРИСОВКА УРОВНЯ (Фона, героев, тварей)
		void DrawBmp(CDC *pDC,bool drowplayer=false);	//| Отрисовка BMP 
		void DrawPlayer(Player *pl,CDC *pDC);			//| Прорисовка игроков
		void FrontBomb(Bomb *bomb);						//| Заполняет массив возможного взрыва и ускоряет взрыв соседних бомб
		void DrawBomb(Bomb *bomb,CDC *pDC,bool b1=true);//| Прорисовка бомбы + её взрыва(true), просто взрыва (false) 
		void DrawBonus(Bonus *b,CDC *pDC);				//| Прорисовка статических бонусов
		void DrawOther(CDC *pDC);						//| Прорисовка остального
		void DrawPause(CDC *pDC,bool b=true);			//| Прорисовка паузы
	
		//** Constructor/destructor 
		Game();                                     
		virtual ~Game();                            	
		//**DEBUG BLOK/////////////////////////////////|
		void Print();
		///////////////////////////////////////////////|	
	protected:
		CBitmap m_VirtScreen,TempScreen;
		CDC		m_VirtScreenDC,TempScreenDC;	
		int level;	
		CFont font,bigfont;
		HBITMAP plusbmp;      
		HBITMAP bumbmp,bomb1bmp,bomb2bmp;// чтобы не грузить 10 раз по 1 мегабайту!
		HBITMAP pausebmp,pause1bmp,bum1bmp,bum2bmp;
	
	public:	
		HBITMAP startbmp,gameoverbmp;
		int L(CPoint &cp1,CPoint &cp2); 
		Player *pl1,*pl2;
		Bomb *bomb[10];
		Bonus *bonus[10];
		char **Matrix; // Динамически выделяется, легче передавать на неё ссылку.
};

#endif // !defined(AFX_GAME_H__17A04225_47C4_47E9_AC16_A13A869E065C__INCLUDED_)
