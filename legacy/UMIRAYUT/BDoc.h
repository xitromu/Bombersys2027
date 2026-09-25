// BDoc.h : interface of the Doc class
//
/////////////////////////////////////////////////////////////////////////////

#if !defined(AFX_BDOC_H__A74B65C9_5632_4B5E_8F50_DF2EDF09F56C__INCLUDED_)
#define AFX_BDOC_H__A74B65C9_5632_4B5E_8F50_DF2EDF09F56C__INCLUDED_

#if _MSC_VER > 1000
#pragma once
#endif // _MSC_VER > 1000


class Doc : public CDocument
{
protected: // create from serialization only
	Doc();
	DECLARE_DYNCREATE(Doc)

// Attributes
public:

// Operations
public:

// Overrides
	// ClassWizard generated virtual function overrides
	//{{AFX_VIRTUAL(Doc)
	public:
	virtual BOOL OnNewDocument();
	virtual void Serialize(CArchive& ar);
	//}}AFX_VIRTUAL

// Implementation
public:
	virtual ~Doc();

// Generated message map functions
protected:
	//{{AFX_MSG(Doc)
	//}}AFX_MSG
	DECLARE_MESSAGE_MAP()
};

/////////////////////////////////////////////////////////////////////////////

//{{AFX_INSERT_LOCATION}}
// Microsoft Visual C++ will insert additional declarations immediately before the previous line.

#endif // !defined(AFX_BDOC_H__A74B65C9_5632_4B5E_8F50_DF2EDF09F56C__INCLUDED_)
