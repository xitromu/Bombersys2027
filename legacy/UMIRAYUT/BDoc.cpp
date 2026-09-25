// BDoc.cpp : implementation of the Doc class
//

#include "stdafx.h"
#include "B.h"

#include "BDoc.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#undef THIS_FILE
static char THIS_FILE[] = __FILE__;
#endif

/////////////////////////////////////////////////////////////////////////////
// Doc

IMPLEMENT_DYNCREATE(Doc, CDocument)

BEGIN_MESSAGE_MAP(Doc, CDocument)
	//{{AFX_MSG_MAP(Doc)
	//}}AFX_MSG_MAP
END_MESSAGE_MAP()

/////////////////////////////////////////////////////////////////////////////
// Doc construction/destruction

Doc::Doc()
{
}

Doc::~Doc()
{

}

BOOL Doc::OnNewDocument()
{
	if (!CDocument::OnNewDocument())
		return FALSE;

	return TRUE;
}



/////////////////////////////////////////////////////////////////////////////
// Doc serialization

void Doc::Serialize(CArchive& ar)
{
	if (ar.IsStoring())
	{
	}
	else
	{
	}
}

