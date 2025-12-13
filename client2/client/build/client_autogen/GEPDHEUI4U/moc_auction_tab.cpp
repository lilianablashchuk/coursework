/****************************************************************************
** Meta object code from reading C++ file 'auction_tab.h'
**
** Created by: The Qt Meta Object Compiler version 68 (Qt 6.4.2)
**
** WARNING! All changes made in this file will be lost!
*****************************************************************************/

#include <memory>
#include "../../../tabs/auction_tab.h"
#include <QtNetwork/QSslError>
#include <QtGui/qtextcursor.h>
#include <QtCore/qmetatype.h>
#if !defined(Q_MOC_OUTPUT_REVISION)
#error "The header file 'auction_tab.h' doesn't include <QObject>."
#elif Q_MOC_OUTPUT_REVISION != 68
#error "This file was generated using the moc from 6.4.2. It"
#error "cannot be used with the include files from this version of Qt."
#error "(The moc has changed too much.)"
#endif

#ifndef Q_CONSTINIT
#define Q_CONSTINIT
#endif

QT_BEGIN_MOC_NAMESPACE
QT_WARNING_PUSH
QT_WARNING_DISABLE_DEPRECATED
namespace {
struct qt_meta_stringdata_AuctionTab_t {
    uint offsetsAndSizes[26];
    char stringdata0[11];
    char stringdata1[14];
    char stringdata2[1];
    char stringdata3[16];
    char stringdata4[20];
    char stringdata5[15];
    char stringdata6[6];
    char stringdata7[12];
    char stringdata8[9];
    char stringdata9[11];
    char stringdata10[12];
    char stringdata11[18];
    char stringdata12[6];
};
#define QT_MOC_LITERAL(ofs, len) \
    uint(sizeof(qt_meta_stringdata_AuctionTab_t::offsetsAndSizes) + ofs), len 
Q_CONSTINIT static const qt_meta_stringdata_AuctionTab_t qt_meta_stringdata_AuctionTab = {
    {
        QT_MOC_LITERAL(0, 10),  // "AuctionTab"
        QT_MOC_LITERAL(11, 13),  // "bidSuccessful"
        QT_MOC_LITERAL(25, 0),  // ""
        QT_MOC_LITERAL(26, 15),  // "refreshAuctions"
        QT_MOC_LITERAL(42, 19),  // "handleAuctionsReply"
        QT_MOC_LITERAL(62, 14),  // "QNetworkReply*"
        QT_MOC_LITERAL(77, 5),  // "reply"
        QT_MOC_LITERAL(83, 11),  // "preserveRow"
        QT_MOC_LITERAL(95, 8),  // "onAddLot"
        QT_MOC_LITERAL(104, 10),  // "onPlaceBid"
        QT_MOC_LITERAL(115, 11),  // "onDeleteLot"
        QT_MOC_LITERAL(127, 17),  // "showAuctionWindow"
        QT_MOC_LITERAL(145, 5)   // "lotId"
    },
    "AuctionTab",
    "bidSuccessful",
    "",
    "refreshAuctions",
    "handleAuctionsReply",
    "QNetworkReply*",
    "reply",
    "preserveRow",
    "onAddLot",
    "onPlaceBid",
    "onDeleteLot",
    "showAuctionWindow",
    "lotId"
};
#undef QT_MOC_LITERAL
} // unnamed namespace

Q_CONSTINIT static const uint qt_meta_data_AuctionTab[] = {

 // content:
      10,       // revision
       0,       // classname
       0,    0, // classinfo
       7,   14, // methods
       0,    0, // properties
       0,    0, // enums/sets
       0,    0, // constructors
       0,       // flags
       1,       // signalCount

 // signals: name, argc, parameters, tag, flags, initial metatype offsets
       1,    0,   56,    2, 0x06,    1 /* Public */,

 // slots: name, argc, parameters, tag, flags, initial metatype offsets
       3,    0,   57,    2, 0x08,    2 /* Private */,
       4,    2,   58,    2, 0x08,    3 /* Private */,
       8,    0,   63,    2, 0x08,    6 /* Private */,
       9,    0,   64,    2, 0x08,    7 /* Private */,
      10,    0,   65,    2, 0x08,    8 /* Private */,
      11,    1,   66,    2, 0x08,    9 /* Private */,

 // signals: parameters
    QMetaType::Void,

 // slots: parameters
    QMetaType::Void,
    QMetaType::Void, 0x80000000 | 5, QMetaType::Int,    6,    7,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void,
    QMetaType::Void, QMetaType::Int,   12,

       0        // eod
};

Q_CONSTINIT const QMetaObject AuctionTab::staticMetaObject = { {
    QMetaObject::SuperData::link<QWidget::staticMetaObject>(),
    qt_meta_stringdata_AuctionTab.offsetsAndSizes,
    qt_meta_data_AuctionTab,
    qt_static_metacall,
    nullptr,
    qt_incomplete_metaTypeArray<qt_meta_stringdata_AuctionTab_t,
        // Q_OBJECT / Q_GADGET
        QtPrivate::TypeAndForceComplete<AuctionTab, std::true_type>,
        // method 'bidSuccessful'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'refreshAuctions'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'handleAuctionsReply'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<QNetworkReply *, std::false_type>,
        QtPrivate::TypeAndForceComplete<int, std::false_type>,
        // method 'onAddLot'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'onPlaceBid'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'onDeleteLot'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        // method 'showAuctionWindow'
        QtPrivate::TypeAndForceComplete<void, std::false_type>,
        QtPrivate::TypeAndForceComplete<int, std::false_type>
    >,
    nullptr
} };

void AuctionTab::qt_static_metacall(QObject *_o, QMetaObject::Call _c, int _id, void **_a)
{
    if (_c == QMetaObject::InvokeMetaMethod) {
        auto *_t = static_cast<AuctionTab *>(_o);
        (void)_t;
        switch (_id) {
        case 0: _t->bidSuccessful(); break;
        case 1: _t->refreshAuctions(); break;
        case 2: _t->handleAuctionsReply((*reinterpret_cast< std::add_pointer_t<QNetworkReply*>>(_a[1])),(*reinterpret_cast< std::add_pointer_t<int>>(_a[2]))); break;
        case 3: _t->onAddLot(); break;
        case 4: _t->onPlaceBid(); break;
        case 5: _t->onDeleteLot(); break;
        case 6: _t->showAuctionWindow((*reinterpret_cast< std::add_pointer_t<int>>(_a[1]))); break;
        default: ;
        }
    } else if (_c == QMetaObject::IndexOfMethod) {
        int *result = reinterpret_cast<int *>(_a[0]);
        {
            using _t = void (AuctionTab::*)();
            if (_t _q_method = &AuctionTab::bidSuccessful; *reinterpret_cast<_t *>(_a[1]) == _q_method) {
                *result = 0;
                return;
            }
        }
    }
}

const QMetaObject *AuctionTab::metaObject() const
{
    return QObject::d_ptr->metaObject ? QObject::d_ptr->dynamicMetaObject() : &staticMetaObject;
}

void *AuctionTab::qt_metacast(const char *_clname)
{
    if (!_clname) return nullptr;
    if (!strcmp(_clname, qt_meta_stringdata_AuctionTab.stringdata0))
        return static_cast<void*>(this);
    return QWidget::qt_metacast(_clname);
}

int AuctionTab::qt_metacall(QMetaObject::Call _c, int _id, void **_a)
{
    _id = QWidget::qt_metacall(_c, _id, _a);
    if (_id < 0)
        return _id;
    if (_c == QMetaObject::InvokeMetaMethod) {
        if (_id < 7)
            qt_static_metacall(this, _c, _id, _a);
        _id -= 7;
    } else if (_c == QMetaObject::RegisterMethodArgumentMetaType) {
        if (_id < 7)
            *reinterpret_cast<QMetaType *>(_a[0]) = QMetaType();
        _id -= 7;
    }
    return _id;
}

// SIGNAL 0
void AuctionTab::bidSuccessful()
{
    QMetaObject::activate(this, &staticMetaObject, 0, nullptr);
}
QT_WARNING_POP
QT_END_MOC_NAMESPACE
