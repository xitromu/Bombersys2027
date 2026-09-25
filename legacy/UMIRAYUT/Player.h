// Player.h: interface for the Player class.
//
//////////////////////////////////////////////////////////////////////

#if !defined(AFX_PLAYER_H__FC408827_F8CC_45B5_BF97_7E1D0983887B__INCLUDED_)
#define AFX_PLAYER_H__FC408827_F8CC_45B5_BF97_7E1D0983887B__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

enum Move {left,right,top,bottom,stop,ltrup,rtrup,btrup,ttrup,sltrup,srtrup,sbtrup,sttrup};
// влево, вправо, вверх, вниз, остановка, 
// смерть влево,смерть вправо, смерть вниз,смерть вверх
// с приставкой "s" - super смерть

enum Sort;
class Bonus;
class Player  
{
	public:		
		HBITMAP playerbmp,facebmp,plusbmp;	//| Загруженные картинки 1) движения персонажа 2) его лицо 
		HBITMAP trupbmp,strupbmp;	        //| 1) его труп 2) эксклюзивный труп
		UINT l,r,t,b,bum;					//| Управление
		Move move,savemove;					//| Направление движения
		char kadr;							//| Текущий номер кадра
		CPoint cpxy,savecpxy;						//| координата на поле
		bool active;						//| true- в игре, false- вне игры
		bool stoptrup;
		bool player1;						//| = true для первого игрока
		CString nameplayer;					//| Имя игрока
		char timetrupx,timetrupy;
		unsigned short n_live,n_bomb;
		UINT score;
	//protected:
	public:
		void FindBonus(Sort sort);
		void NextStep(char **Matrix,Bonus *bonus[10]);	
	//| Constructor/destructor |//////////|
	Player(bool b,CString name,CString files,UINT a1,UINT a2,UINT a3,UINT a4,UINT a5,int i,int j,bool active=false);
	virtual ~Player() {};                  
};
#endif // !defined(AFX_PLAYER_H__FC408827_F8CC_45B5_BF97_7E1D0983887B__INCLUDED_)
