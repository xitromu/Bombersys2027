// BView.h : interface of the BView class
//
/////////////////////////////////////////////////////////////////////////////

#if !defined(AFX_BVIEW_H__DE70807D_E470_4198_BC5B_9D44AEC05FF7__INCLUDED_)
#define AFX_BVIEW_H__DE70807D_E470_4198_BC5B_9D44AEC05FF7__INCLUDED_
	
#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

#define PLAYERSPEED 3
#define BOMBASPEED 7
#define ID_TIMER 30
#include <time.h>

class Game;
enum Screen {start,action,gameover};
class BView : public CView
{
protected: // create from serialization only
	BView();
	DECLARE_DYNCREATE(BView)

// Attributes
public:
	Doc* GetDocument();
public:
// Overrides
	// ClassWizard generated virtual function overrides
	//{{AFX_VIRTUAL(BView)
	public:
	virtual void OnDraw(CDC* pDC);  // overridden to draw this view
	protected:
	//}}AFX_VIRTUAL

// Implementation
public:
	CBitmap m_VirtScreen;
	CDC		m_VirtScreenDC;		

	Game *game;
	CRect saverect;
	bool newlevel;
	bool pause,pause1;
	Screen screen;
	unsigned int playertime,bombatime,timestart;

	virtual ~BView();
// Generated message map functions
protected:
	//{{AFX_MSG(BView)
	afx_msg BOOL OnEraseBkgnd(CDC* pDC) {return 0;};
	afx_msg int OnCreate(LPCREATESTRUCT lpCreateStruct);
	afx_msg void OnKeyDown(UINT nChar, UINT nRepCnt, UINT nFlags);
	afx_msg void OnTimer(UINT nIDEvent);
	afx_msg void OnKeyUp(UINT nChar, UINT nRepCnt, UINT nFlags);
	//}}AFX_MSG
	DECLARE_MESSAGE_MAP()
};

#ifndef _DEBUG  // debug version in BView.cpp
inline Doc* BView::GetDocument()
   { return (Doc*)m_pDocument; }
#endif

/////////////////////////////////////////////////////////////////////////////

//{{AFX_INSERT_LOCATION}}
// Microsoft Visual C++ will insert additional declarations immediately before the previous line.

#endif // !defined(AFX_BVIEW_H__DE70807D_E470_4198_BC5B_9D44AEC05FF7__INCLUDED_)
