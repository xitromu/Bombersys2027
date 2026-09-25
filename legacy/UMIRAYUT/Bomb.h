// Bomb.h: interface for the Bomb class.
//
//////////////////////////////////////////////////////////////////////

#if !defined(AFX_BOMB_H__3EF798DB_A253_40BF_A1F0_2DC8C02AD001__INCLUDED_)
#define AFX_BOMB_H__3EF798DB_A253_40BF_A1F0_2DC8C02AD001__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

#define DETONATION 50

class Bomb  
{
	public:		
		bool NextStep();
		Bomb(bool pl,int x,int y,bool b);
		bool active;
		bool bb[4];;
		bool player1;
		char savekadr,kadr;							//| “екущий номер кадра
		CPoint cpxy;						//| координата на поле
		UINT temp;
		CPoint bumb[9];						//| массив возможного взрыва

	//| Constructor/destructor |//////////|
	virtual ~Bomb(){};                  
};

// «она взрыва- массив bumb
//        6     
//        2
//    5 1 0 3 7
//		  4	
//		  8	



#endif // !defined(AFX_BOMB_H__3EF798DB_A253_40BF_A1F0_2DC8C02AD001__INCLUDED_)
