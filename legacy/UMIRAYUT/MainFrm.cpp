// MainFrm.cpp : implementation of the Frame class
//

#include "stdafx.h"
#include "B.h"

#include "MainFrm.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#undef THIS_FILE
static char THIS_FILE[] = __FILE__;
#endif

/////////////////////////////////////////////////////////////////////////////
// Frame

IMPLEMENT_DYNCREATE(Frame, CFrameWnd)

BEGIN_MESSAGE_MAP(Frame, CFrameWnd)
	//{{AFX_MSG_MAP(Frame)
	//}}AFX_MSG_MAP
END_MESSAGE_MAP()

/////////////////////////////////////////////////////////////////////////////
// Frame construction/destruction

Frame::Frame()
{
}

Frame::~Frame()
{
}

BOOL Frame::PreCreateWindow(CREATESTRUCT& cs)
{
	if( !CFrameWnd::PreCreateWindow(cs) )
		return FALSE;
	cs.style =WS_POPUPWINDOW|CS_BYTEALIGNCLIENT;//Без верхушки.
	cs.cx=1024;//Здесь задаются размеры и стиль окна
	cs.cy=768;
	return TRUE;
}
