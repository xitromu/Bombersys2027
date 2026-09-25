// Bonus.h: interface for the Bonus class.
//
//////////////////////////////////////////////////////////////////////

#if !defined(AFX_BONUS_H__E2065F0A_CBB4_43FD_B074_8A904B799D50__INCLUDED_)
#define AFX_BONUS_H__E2065F0A_CBB4_43FD_B074_8A904B799D50__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000


enum Sort {door,sunduk,bomba,live,smert,meshok,bigmeshok,bruliki,nasledstvo};
class Bonus  
{
	public:
		bool active;
		bool on_off;
		CPoint cpxy;		//| координата на поле
		Sort sort;
		HBITMAP bonusbmp;
	
	public:
		void ReplaceBmp();
		Bonus(Sort s);
		Bonus();
	virtual ~Bonus();

};

#endif // !defined(AFX_BONUS_H__E2065F0A_CBB4_43FD_B074_8A904B799D50__INCLUDED_)





