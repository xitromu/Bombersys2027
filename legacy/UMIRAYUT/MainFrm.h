// MainFrm.h : interface of the Frame class
//
/////////////////////////////////////////////////////////////////////////////

#if !defined(AFX_MAINFRM_H__1E1068FD_6E1F_40DF_9421_19087D24642F__INCLUDED_)
#define AFX_MAINFRM_H__1E1068FD_6E1F_40DF_9421_19087D24642F__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

class Frame : public CFrameWnd
{
	
protected: // create from serialization only
	Frame();
	DECLARE_DYNCREATE(Frame)

// Attributes
public:

// Operations
public:

// Overrides
	// ClassWizard generated virtual function overrides
	//{{AFX_VIRTUAL(Frame)
	public:
	virtual BOOL PreCreateWindow(CREATESTRUCT& cs);
	//}}AFX_VIRTUAL

// Implementation
public:
	virtual ~Frame();


// Generated message map functions
protected:
	//{{AFX_MSG(Frame)
	//}}AFX_MSG
	DECLARE_MESSAGE_MAP()
};

/////////////////////////////////////////////////////////////////////////////

//{{AFX_INSERT_LOCATION}}
// Microsoft Visual C++ will insert additional declarations immediately before the previous line.

#endif // !defined(AFX_MAINFRM_H__1E1068FD_6E1F_40DF_9421_19087D24642F__INCLUDED_)
