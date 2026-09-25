// B.h : main header file for the B application
//

#if !defined(AFX_B_H__5F892F4E_8CEC_4B5E_97CD_2434469FAD2F__INCLUDED_)
#define AFX_B_H__5F892F4E_8CEC_4B5E_97CD_2434469FAD2F__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000

#ifndef __AFXWIN_H__
	#error include 'stdafx.h' before including this file for PCH
#endif

#include "resource.h"       // main symbols

/////////////////////////////////////////////////////////////////////////////
// App:
// See B.cpp for the implementation of this class
//

class App : public CWinApp
{
public:
	App();

// Overrides
	// ClassWizard generated virtual function overrides
	//{{AFX_VIRTUAL(App)
	public:
	virtual BOOL InitInstance();
	//}}AFX_VIRTUAL

// Implementation
	//{{AFX_MSG(App)
	afx_msg void OnAppAbout();
	//}}AFX_MSG
	DECLARE_MESSAGE_MAP()
};


/////////////////////////////////////////////////////////////////////////////

//{{AFX_INSERT_LOCATION}}
// Microsoft Visual C++ will insert additional declarations immediately before the previous line.

#endif // !defined(AFX_B_H__5F892F4E_8CEC_4B5E_97CD_2434469FAD2F__INCLUDED_)
